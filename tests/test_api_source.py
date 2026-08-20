import json

import pandas as pd
import pytest
import requests

from src import agent_engine
from src.data_query_engine import query_dataset
from src.data_sources import api_source
from src.llm.base import LLMProviderError


class Response:
    def __init__(self, payload=None, *, status=200, content_type="application/json", content_length=None):
        self.status_code = status
        self.headers = {"content-type": content_type}
        self._body = json.dumps(payload).encode("utf-8") if payload is not None else b""
        if content_length is not None:
            self.headers["content-length"] = str(content_length)

    def iter_content(self, chunk_size):
        yield self._body


@pytest.fixture(autouse=True)
def public_url(monkeypatch):
    monkeypatch.setattr(api_source, "validate_api_url", lambda url: "https://example.com/data")


def fetch(monkeypatch, response):
    monkeypatch.setattr(api_source.requests, "get", lambda *args, **kwargs: response)


def test_successful_json_array(monkeypatch):
    fetch(monkeypatch, Response([{"region": "North", "profit": 300}, {"region": "South", "profit": 450}]))
    result = api_source.fetch_api_data("https://example.com/data")
    assert result.status == "success" and result.rows == 2
    assert result.columns == ["region", "profit"]


def test_wrapped_json_data_and_nested_normalization(monkeypatch):
    fetch(monkeypatch, Response({"data": [{"region": "South", "metrics": {"profit": 450}}]}))
    result = api_source.fetch_api_data("https://example.com/data")
    assert result.status == "success"
    assert result.dataframe.loc[0, "metrics.profit"] == 450


def test_empty_and_malformed_response_are_rejected(monkeypatch):
    fetch(monkeypatch, Response([]))
    assert "empty dataset" in api_source.fetch_api_data("https://example.com/data").error
    response = Response(None)
    response._body = b"not-json"
    fetch(monkeypatch, response)
    assert "Expecting value" in api_source.fetch_api_data("https://example.com/data").error


@pytest.mark.parametrize("status", [400, 404, 500])
def test_http_errors_are_controlled(monkeypatch, status):
    fetch(monkeypatch, Response([], status=status))
    result = api_source.fetch_api_data("https://example.com/data")
    assert result.status == "error" and str(status) in result.error


def test_timeout_and_oversized_responses_are_controlled(monkeypatch):
    monkeypatch.setattr(api_source.requests, "get", lambda *args, **kwargs: (_ for _ in ()).throw(requests.Timeout()))
    assert "timed out" in api_source.fetch_api_data("https://example.com/data").error
    fetch(monkeypatch, Response([], content_length=99 * 1024 * 1024))
    assert "size limit" in api_source.fetch_api_data("https://example.com/data").error


def test_non_json_and_unsupported_payloads_are_rejected(monkeypatch):
    fetch(monkeypatch, Response([{"region": "South"}], content_type="text/html"))
    assert "content type" in api_source.fetch_api_data("https://example.com/data").error
    fetch(monkeypatch, Response({"message": "not tabular"}))
    assert "array of objects" in api_source.fetch_api_data("https://example.com/data").error


def test_streamed_oversize_is_rejected(monkeypatch):
    class LargeResponse(Response):
        def __init__(self):
            super().__init__([])
            self.headers = {"content-type": "application/json"}
        def iter_content(self, chunk_size):
            yield b"x" * (11 * 1024 * 1024)
    fetch(monkeypatch, LargeResponse())
    assert "size limit" in api_source.fetch_api_data("https://example.com/data").error


def test_headers_and_parameters_are_passed_without_result_metadata(monkeypatch):
    captured = {}
    def get(*args, **kwargs):
        captured.update(kwargs)
        return Response([{"region": "South"}])
    monkeypatch.setattr(api_source.requests, "get", get)
    result = api_source.fetch_api_data("https://example.com/data", params={"limit": 1}, headers={"Authorization": "Bearer hidden"})
    assert captured["params"] == {"limit": 1}
    assert captured["headers"]["Authorization"] == "Bearer hidden"
    assert "Authorization" not in str(result.metadata)


@pytest.mark.parametrize("url", ["ftp://example.com/a", "http://localhost/a", "http://127.0.0.1/a", "http://10.0.0.2/a", "http://169.254.169.254/latest/meta-data"])
def test_unsafe_urls_are_blocked(monkeypatch, url):
    monkeypatch.undo()
    monkeypatch.setattr(api_source.socket, "getaddrinfo", lambda *args, **kwargs: [(None, None, None, None, ("93.184.216.34", 0))])
    if "127.0.0.1" in url or "10.0.0.2" in url or "169.254" in url:
        host = url.split("//", 1)[1].split("/", 1)[0]
        monkeypatch.setattr(api_source.socket, "getaddrinfo", lambda *args, **kwargs: [(None, None, None, None, (host, 0))])
    with pytest.raises(ValueError):
        api_source.validate_api_url(url)


def test_api_frame_enters_existing_profile_and_deterministic_analysis(monkeypatch):
    fetch(monkeypatch, Response([
        {"region": "North", "revenue": 1000, "profit": 300},
        {"region": "South", "revenue": 1500, "profit": 450},
        {"region": "East", "revenue": 700, "profit": 100},
        {"region": "West", "revenue": 1200, "profit": 360},
    ]))
    result = api_source.fetch_api_data("https://example.com/data")
    assert result.metadata["profile"]["rows"] == 4
    answer = query_dataset(result.dataframe, "Which region has the highest profit?")
    assert "South" in answer and "450.00" in answer


def test_api_frame_enters_autonomous_fallback_without_source_specific_logic(monkeypatch):
    fetch(monkeypatch, Response([
        {"region": "North", "revenue": 1000, "profit": 300},
        {"region": "South", "revenue": 1500, "profit": 450},
    ]))
    class UnavailableProvider:
        def generate_plan(self, *args, **kwargs):
            raise LLMProviderError("unavailable")
        def generate_narrative(self, *args, **kwargs):
            raise LLMProviderError("unavailable")
    monkeypatch.setattr(agent_engine, "get_llm_provider", lambda: UnavailableProvider())
    result = agent_engine.run_autonomous_analysis(
        api_source.fetch_api_data("https://example.com/data").dataframe,
        "Why is South the most profitable region?",
    )
    assert result["mode"] == "agent"
    assert result["status"] == "success_with_fallback"
    assert result["root_cause"]["observation"].startswith("South")

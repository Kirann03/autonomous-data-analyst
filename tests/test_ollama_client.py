import pytest
import requests

from src import ollama_client


def test_ollama_connection_error_is_sanitized(monkeypatch):
    monkeypatch.setattr(ollama_client.requests, "post", lambda *args, **kwargs: (_ for _ in ()).throw(requests.exceptions.ConnectionError()))
    with pytest.raises(ollama_client.OllamaError, match="Could not connect"):
        ollama_client.generate_text("hello")


def test_ollama_malformed_response_is_rejected(monkeypatch):
    class Response:
        ok = True
        status_code = 200
        headers = {}
        text = ""

        def raise_for_status(self):
            return None
        def json(self):
            return {"not_response": "x"}
    monkeypatch.setattr(ollama_client.requests, "post", lambda *args, **kwargs: Response())
    with pytest.raises(ollama_client.OllamaError, match="did not contain"):
        ollama_client.generate_text("hello")


def test_ollama_json_mode_uses_structured_payload(monkeypatch):
    captured = {}

    class Response:
        ok = True
        status_code = 200
        headers = {}
        text = ""

        def raise_for_status(self):
            return None

        def json(self):
            return {"response": "{}"}

    def post(*args, **kwargs):
        captured.update(kwargs["json"])
        return Response()

    monkeypatch.setattr(ollama_client.requests, "post", post)
    assert ollama_client.generate_text("plan", json_mode=True) == "{}"
    assert captured["format"] == "json"
    assert captured["think"] is False

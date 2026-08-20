"""Bounded, user-initiated REST JSON ingestion for the shared analytics pipeline."""

from __future__ import annotations

import ipaddress
import json
import os
import socket
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import pandas as pd
import requests

from src.config import load_project_environment
from src.dataset_profiler import profile_dataset
from src.date_analysis import detect_date_columns


DEFAULT_TIMEOUT_SECONDS = 15
MAX_REDIRECTS = 0


@dataclass
class APIDataResult:
    status: str
    dataframe: pd.DataFrame | None = None
    rows: int = 0
    columns: list[str] = field(default_factory=list)
    source_url: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


def _max_response_bytes() -> int:
    load_project_environment()
    return max(1, int(os.getenv("API_MAX_RESPONSE_MB", "10"))) * 1024 * 1024


def _safe_source_url(url: str) -> str:
    parsed = urlsplit(url)
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))


def _blocked_ip(address: str) -> bool:
    ip = ipaddress.ip_address(address)
    return any((ip.is_private, ip.is_loopback, ip.is_link_local, ip.is_reserved, ip.is_unspecified, ip.is_multicast))


def validate_api_url(url: str) -> str:
    """Validate a public HTTP(S) endpoint and reject obvious SSRF destinations."""
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("API URL must use http or https.")
    if not parsed.hostname:
        raise ValueError("API URL must include a hostname.")
    hostname = parsed.hostname.lower().rstrip(".")
    if hostname == "localhost" or hostname.endswith(".localhost") or hostname in {"metadata.google.internal", "metadata"}:
        raise ValueError("Internal or metadata API hosts are not allowed.")
    try:
        addresses = {item[4][0] for item in socket.getaddrinfo(hostname, None, type=socket.SOCK_STREAM)}
    except socket.gaierror as error:
        raise ValueError("API hostname could not be resolved.") from error
    if not addresses or any(_blocked_ip(address) for address in addresses):
        raise ValueError("Private, loopback, link-local, or reserved API addresses are not allowed.")
    return _safe_source_url(url)


def _records_from_payload(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list) and all(isinstance(item, dict) for item in payload):
        return payload
    if isinstance(payload, dict):
        for key in ("data", "results", "items", "records"):
            value = payload.get(key)
            if isinstance(value, list) and all(isinstance(item, dict) for item in value):
                return value
    raise ValueError("API JSON must be an array of objects or a simple object containing one.")


def _result_from_frame(frame: pd.DataFrame, source_url: str, metadata: dict[str, Any]) -> APIDataResult:
    if frame.empty:
        return APIDataResult("error", source_url=source_url, metadata=metadata, error="API response produced an empty dataset.")
    profile = profile_dataset(frame)
    metadata["data_quality"] = {
        "duplicate_rows": int(frame.duplicated().sum()),
        "missing_values": int(frame.isna().sum().sum()),
        "numeric_columns": frame.select_dtypes(include="number").columns.astype(str).tolist(),
        "categorical_columns": frame.select_dtypes(include=["object", "string", "category"]).columns.astype(str).tolist(),
        "date_columns": detect_date_columns(frame),
    }
    metadata["profile"] = profile
    return APIDataResult("success", frame, len(frame), frame.columns.astype(str).tolist(), source_url, metadata)


def fetch_api_data(url: str, method: str = "GET", params: dict[str, Any] | None = None,
                   headers: dict[str, str] | None = None, timeout: int = DEFAULT_TIMEOUT_SECONDS) -> APIDataResult:
    """Fetch a public JSON GET response into a DataFrame without logging user headers."""
    source_url = ""
    try:
        if method.upper() != "GET":
            raise ValueError("Only HTTP GET is supported for API ingestion.")
        source_url = validate_api_url(url)
        limit = _max_response_bytes()
        response = requests.get(url, params=params, headers=headers, timeout=(min(timeout, 10), timeout),
                                stream=True, allow_redirects=False)
        metadata = {"http_status": response.status_code, "content_type": response.headers.get("content-type", "").split(";", 1)[0]}
        if 300 <= response.status_code < 400:
            return APIDataResult("error", source_url=source_url, metadata=metadata, error="API redirects are not supported.")
        if response.status_code >= 400:
            return APIDataResult("error", source_url=source_url, metadata=metadata, error=f"API returned HTTP {response.status_code}.")
        content_length = response.headers.get("content-length")
        if content_length and int(content_length) > limit:
            return APIDataResult("error", source_url=source_url, metadata=metadata, error="API response exceeds the configured size limit.")
        chunks, total = [], 0
        for chunk in response.iter_content(chunk_size=64 * 1024):
            if not chunk:
                continue
            total += len(chunk)
            if total > limit:
                return APIDataResult("error", source_url=source_url, metadata=metadata, error="API response exceeds the configured size limit.")
            chunks.append(chunk)
        metadata["response_bytes"] = total
        if not chunks:
            return APIDataResult("error", source_url=source_url, metadata=metadata, error="API response was empty.")
        if "json" not in metadata["content_type"].lower():
            return APIDataResult("error", source_url=source_url, metadata=metadata, error="API response content type must be JSON.")
        payload = json.loads(b"".join(chunks).decode("utf-8"))
        frame = pd.json_normalize(_records_from_payload(payload), sep=".")
        return _result_from_frame(frame, source_url, metadata)
    except requests.Timeout:
        return APIDataResult("error", source_url=source_url, error="API request timed out.")
    except requests.RequestException:
        return APIDataResult("error", source_url=source_url, error="API request failed.")
    except (ValueError, json.JSONDecodeError) as error:
        return APIDataResult("error", source_url=source_url, error=str(error))

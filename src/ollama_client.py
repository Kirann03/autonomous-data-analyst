"""Small configuration-driven client for the local Ollama generation API."""

from __future__ import annotations

import logging
import os
import requests
from src.config import PROJECT_ROOT, load_project_environment


logger = logging.getLogger(__name__)


class OllamaError(RuntimeError):
    """Raised when Ollama cannot return a usable generation response."""

    def __init__(self, message: str, *, failure_type: str = "client_error", status: int | None = None,
                 response_length: int | None = None, response_preview: str = ""):
        super().__init__(message)
        self.failure_type = failure_type
        self.status = status
        self.response_length = response_length
        self.response_preview = response_preview


def get_ollama_config() -> tuple[str, str, int]:
    """Load non-secret Ollama configuration from the project-root .env file."""
    load_project_environment()
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
    model = os.getenv("OLLAMA_MODEL", "qwen3:8b")
    timeout = int(os.getenv("OLLAMA_TIMEOUT", "120"))
    return base_url, model, timeout


def generate_text(
    prompt: str, *, timeout: int | None = None, json_mode: bool = False
) -> str:
    """Generate text through Ollama and reject malformed/non-text responses."""
    base_url, model, configured_timeout = get_ollama_config()
    response = None
    try:
        request_payload = {"model": model, "prompt": prompt, "stream": False}
        if json_mode:
            request_payload.update({"format": "json", "think": False, "options": {"num_predict": 160}})
        response = requests.post(
            f"{base_url}/api/generate",
            json=request_payload,
            timeout=timeout or configured_timeout,
        )
    except requests.exceptions.ConnectionError as error:
        raise OllamaError("Could not connect to local Ollama. Start Ollama and try again.", failure_type="connection") from error
    except requests.exceptions.Timeout as error:
        raise OllamaError("Ollama request timed out.", failure_type="timeout") from error
    except requests.RequestException as error:
        raise OllamaError("Ollama request failed.", failure_type="network") from error
    if not response.ok:
        body = response.text or ""
        preview = body[:1000]
        logger.debug("Ollama failure: status=%s type=%s empty=%s length=%s body=%r", response.status_code,
                     response.headers.get("content-type", ""), not bool(body), len(body), preview)
        raise OllamaError(f"Ollama HTTP {response.status_code}.", failure_type="http_error",
                          status=response.status_code, response_length=len(body), response_preview=preview)
    try:
        payload = response.json()
    except ValueError as error:
        body = response.text or ""
        preview = body[:1000]
        logger.debug("Ollama malformed HTTP body: status=%s type=%s empty=%s length=%s body=%r", response.status_code,
                     response.headers.get("content-type", ""), not bool(body), len(body), preview)
        raise OllamaError("Ollama returned a non-JSON HTTP response.", failure_type="http_body",
                          status=response.status_code, response_length=len(body), response_preview=preview) from error
    text = payload.get("response") if isinstance(payload, dict) else None
    if not isinstance(text, str) or not text.strip():
        raw_body = response.text or ""
        logger.debug("Ollama empty model response: status=%s type=%s empty=%s length=%s body=%r", response.status_code,
                     response.headers.get("content-type", ""), not bool(raw_body), len(raw_body), raw_body[:1000])
        raise OllamaError("Ollama response did not contain generated text.", failure_type="empty_model_response",
                          status=response.status_code, response_length=len(raw_body), response_preview=raw_body[:1000])
    logger.debug("Ollama model response: status=%s type=%s empty=%s length=%s text=%r", response.status_code,
                 response.headers.get("content-type", ""), False, len(text), text[:1000])
    return text.strip()

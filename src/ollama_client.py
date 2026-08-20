"""Small configuration-driven client for the local Ollama generation API."""

from __future__ import annotations

import os
from pathlib import Path

import requests
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class OllamaError(RuntimeError):
    """Raised when Ollama cannot return a usable generation response."""


def get_ollama_config() -> tuple[str, str, int]:
    """Load non-secret Ollama configuration from the project-root .env file."""
    load_dotenv(PROJECT_ROOT / ".env")
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
    model = os.getenv("OLLAMA_MODEL", "qwen3:8b")
    timeout = int(os.getenv("OLLAMA_TIMEOUT", "120"))
    return base_url, model, timeout


def generate_text(prompt: str, *, timeout: int | None = None) -> str:
    """Generate text through Ollama and reject malformed/non-text responses."""
    base_url, model, configured_timeout = get_ollama_config()
    try:
        response = requests.post(
            f"{base_url}/api/generate",
            json={"model": model, "prompt": prompt, "stream": False},
            timeout=timeout or configured_timeout,
        )
        response.raise_for_status()
        payload = response.json()
    except requests.exceptions.ConnectionError as error:
        raise OllamaError("Could not connect to local Ollama. Start Ollama and try again.") from error
    except requests.exceptions.Timeout as error:
        raise OllamaError("Ollama request timed out.") from error
    except (requests.RequestException, ValueError) as error:
        raise OllamaError("Ollama returned an invalid response.") from error
    text = payload.get("response") if isinstance(payload, dict) else None
    if not isinstance(text, str) or not text.strip():
        raise OllamaError("Ollama response did not contain generated text.")
    return text.strip()

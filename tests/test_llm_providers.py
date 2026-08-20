import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.llm.base import LLMProviderError
from src.llm.factory import FallbackProvider, get_llm_provider, get_llm_provider_label
from src.llm.ollama_provider import OllamaProvider
from src.llm.openai_provider import OpenAIProvider
from src.ollama_client import OllamaError


def test_ollama_provider_uses_json_mode(monkeypatch):
    captured = {}
    monkeypatch.setattr("src.llm.ollama_provider.generate_text", lambda prompt, **kwargs: captured.update(kwargs) or "{}")
    assert OllamaProvider().generate_plan("plan", timeout=5) == "{}"
    assert captured == {"timeout": 5, "json_mode": True}


def test_ollama_provider_wraps_errors(monkeypatch):
    monkeypatch.setattr("src.llm.ollama_provider.generate_text", lambda *args, **kwargs: (_ for _ in ()).throw(OllamaError("network")))
    with pytest.raises(LLMProviderError, match="Ollama planner failure"):
        OllamaProvider().generate_plan("plan")


def test_openai_provider_structured_plan(monkeypatch):
    captured = {}

    class Client:
        class responses:
            @staticmethod
            def create(**kwargs):
                captured.update(kwargs)
                return SimpleNamespace(output_text='{"steps":[]}')

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_MODEL", "test-model")
    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(OpenAI=lambda **kwargs: Client()))
    assert OpenAIProvider().generate_plan("plan", timeout=4) == '{"steps":[]}'
    assert captured["model"] == "test-model"
    assert captured["text"]["format"]["type"] == "json_object"


def test_openai_provider_missing_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(LLMProviderError, match="OPENAI_API_KEY"):
        OpenAIProvider()


def test_openai_provider_api_error_is_sanitized(monkeypatch):
    class Client:
        class responses:
            @staticmethod
            def create(**kwargs):
                raise RuntimeError("secret should not appear")

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(OpenAI=lambda **kwargs: Client()))
    with pytest.raises(LLMProviderError, match="OpenAI request failed") as error:
        OpenAIProvider().generate_narrative("prompt")
    assert "secret" not in str(error.value)


def test_openai_provider_rejects_malformed_plan(monkeypatch):
    class Client:
        class responses:
            @staticmethod
            def create(**kwargs):
                return SimpleNamespace(output_text="not json")

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(OpenAI=lambda **kwargs: Client()))
    with pytest.raises(LLMProviderError, match="valid JSON"):
        OpenAIProvider().generate_plan("plan")


def test_provider_factory_selects_ollama(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    monkeypatch.setenv("LLM_FALLBACK_ENABLED", "false")
    assert isinstance(get_llm_provider(), OllamaProvider)


def test_provider_factory_rejects_invalid_provider(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "invalid")
    with pytest.raises(LLMProviderError, match="Unsupported"):
        get_llm_provider()


def test_provider_labels_are_safe_and_explicit(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    assert get_llm_provider_label() == "qwen3"
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    assert get_llm_provider_label() == "openai"


def test_provider_fallback_uses_secondary_only_after_primary_failure():
    class Primary:
        def generate_plan(self, prompt, *, timeout=None):
            raise LLMProviderError("ollama unavailable")
        def generate_narrative(self, prompt, *, timeout=None):
            raise LLMProviderError("ollama unavailable")

    class Secondary:
        def generate_plan(self, prompt, *, timeout=None):
            return "{}"
        def generate_narrative(self, prompt, *, timeout=None):
            return "narrative"

    provider = FallbackProvider(Primary(), Secondary())
    assert provider.generate_plan("plan") == "{}"
    assert provider.generate_narrative("narrative") == "narrative"


def test_openai_provider_has_no_ollama_implementation_import():
    source = Path("src/llm/openai_provider.py").read_text(encoding="utf-8")
    assert "src.ollama_client" not in source

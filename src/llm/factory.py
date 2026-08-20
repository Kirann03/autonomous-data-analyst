"""Explicit provider selection and optional Ollama-to-OpenAI fallback."""

from __future__ import annotations

import os

from src.config import load_project_environment
from src.llm.base import LLMProvider, LLMProviderError
from src.llm.ollama_provider import OllamaProvider


class FallbackProvider:
    """Use the explicitly configured secondary provider only after primary failure."""

    def __init__(self, primary: LLMProvider, secondary: LLMProvider) -> None:
        self.primary, self.secondary = primary, secondary

    def generate_plan(self, prompt: str, *, timeout: int | None = None) -> str:
        try:
            return self.primary.generate_plan(prompt, timeout=timeout)
        except LLMProviderError:
            return self.secondary.generate_plan(prompt, timeout=timeout)

    def generate_narrative(self, prompt: str, *, timeout: int | None = None) -> str:
        try:
            return self.primary.generate_narrative(prompt, timeout=timeout)
        except LLMProviderError:
            return self.secondary.generate_narrative(prompt, timeout=timeout)


def get_llm_provider() -> LLMProvider:
    """Build the selected provider; no provider is auto-selected without config."""
    load_project_environment()
    provider_name = os.getenv("LLM_PROVIDER", "ollama").strip().lower()
    if provider_name == "ollama":
        primary: LLMProvider = OllamaProvider()
        if os.getenv("LLM_FALLBACK_ENABLED", "false").strip().lower() == "true":
            from src.llm.openai_provider import OpenAIProvider
            return FallbackProvider(primary, OpenAIProvider())
        return primary
    if provider_name == "openai":
        from src.llm.openai_provider import OpenAIProvider
        return OpenAIProvider()
    raise LLMProviderError(f"Unsupported LLM_PROVIDER: {provider_name}.")


def get_llm_timeout() -> int:
    """Return the shared LLM timeout while retaining the existing Ollama setting."""
    load_project_environment()
    return int(os.getenv("LLM_TIMEOUT", os.getenv("OLLAMA_TIMEOUT", "120")))


def get_llm_provider_label() -> str:
    """Return a safe, display-only label for the explicitly selected provider."""
    load_project_environment()
    provider_name = os.getenv("LLM_PROVIDER", "ollama").strip().lower()
    return "qwen3" if provider_name == "ollama" else provider_name

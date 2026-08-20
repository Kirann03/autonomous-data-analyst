"""Ollama implementation of the minimal LLM provider contract."""

from __future__ import annotations

from src.llm.base import LLMProviderError
from src.ollama_client import OllamaError, generate_text


class OllamaProvider:
    """Local Qwen3/Ollama provider; structured plans use Ollama JSON mode."""

    def generate_plan(self, prompt: str, *, timeout: int | None = None) -> str:
        try:
            return generate_text(prompt, timeout=timeout, json_mode=True)
        except OllamaError as error:
            raise LLMProviderError(f"Ollama planner failure: {error}") from error

    def generate_narrative(self, prompt: str, *, timeout: int | None = None) -> str:
        try:
            return generate_text(prompt, timeout=timeout)
        except OllamaError as error:
            raise LLMProviderError(f"Ollama narrative failure: {error}") from error

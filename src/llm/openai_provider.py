"""Optional OpenAI implementation of the minimal LLM provider contract."""

from __future__ import annotations

import json
import os

from src.config import load_project_environment
from src.llm.base import LLMProviderError


class OpenAIProvider:
    """OpenAI Responses API provider, initialized only when explicitly selected."""

    def __init__(self) -> None:
        load_project_environment()
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise LLMProviderError("OPENAI_API_KEY is required when LLM_PROVIDER=openai.")
        self.model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
        try:
            from openai import OpenAI
        except ImportError as error:
            raise LLMProviderError("The optional openai package is not installed.") from error
        self._client = OpenAI(api_key=api_key)

    def _generate(self, prompt: str, *, timeout: int | None, json_mode: bool) -> str:
        kwargs = {"model": self.model, "input": prompt}
        if timeout is not None:
            kwargs["timeout"] = timeout
        if json_mode:
            kwargs["text"] = {"format": {"type": "json_object"}}
        try:
            response = self._client.responses.create(**kwargs)
            text = getattr(response, "output_text", "")
        except Exception as error:
            raise LLMProviderError("OpenAI request failed.") from error
        if not isinstance(text, str) or not text.strip():
            raise LLMProviderError("OpenAI response did not contain generated text.")
        if json_mode:
            try:
                json.loads(text)
            except json.JSONDecodeError as error:
                raise LLMProviderError("OpenAI planner response was not valid JSON.") from error
        return text.strip()

    def generate_plan(self, prompt: str, *, timeout: int | None = None) -> str:
        return self._generate(prompt, timeout=timeout, json_mode=True)

    def generate_narrative(self, prompt: str, *, timeout: int | None = None) -> str:
        return self._generate(prompt, timeout=timeout, json_mode=False)

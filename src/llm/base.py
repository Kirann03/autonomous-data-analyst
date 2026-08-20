"""Minimal LLM contract for planning and evidence-grounded narratives."""

from __future__ import annotations

from typing import Protocol


class LLMProviderError(RuntimeError):
    """A safe provider failure that never includes credentials."""


class LLMProvider(Protocol):
    """The only two LLM operations required by the analyst."""

    def generate_plan(self, prompt: str, *, timeout: int | None = None) -> str:
        """Return structured planner text."""

    def generate_narrative(self, prompt: str, *, timeout: int | None = None) -> str:
        """Return narrative text grounded in provided evidence."""

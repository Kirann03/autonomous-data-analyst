"""Provider-agnostic LLM interfaces used by the controlled analyst."""

from src.llm.factory import get_llm_provider

__all__ = ["get_llm_provider"]

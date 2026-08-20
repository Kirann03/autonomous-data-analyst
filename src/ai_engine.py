"""AI analysis prompts backed by the selected LLM provider."""

import json

from src.llm.base import LLMProviderError
from src.llm.factory import get_llm_provider


def ask_llama(prompt: str) -> str:
    """Compatibility wrapper for existing AI features using the selected provider."""
    try:
        return get_llm_provider().generate_narrative(prompt)
    except LLMProviderError as error:
        return f"❌ AI error: {error}"


def generate_analysis(dataset_summary, question):
    prompt = f"""
You are an AI Data Analyst. Analyze only the dataset information supplied below.
Do not invent numbers or columns. Separate facts from interpretations and be concise.

DATASET INFORMATION:
{json.dumps(dataset_summary, indent=2, default=str)}

USER QUESTION:
{question}
"""
    return ask_llama(prompt)

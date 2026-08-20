"""AI analysis prompts backed by the shared local Ollama client."""

import json

from src.ollama_client import OllamaError, generate_text


def ask_llama(prompt: str) -> str:
    """Keep the existing text-returning interface while using central configuration."""
    try:
        return generate_text(prompt)
    except OllamaError as error:
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

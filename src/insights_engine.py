"""Executive-insight prompt backed by the shared local Ollama client."""

from src.ai_engine import ask_llama


def generate_business_insights(dataset_summary):
    ai_context = dataset_summary.get("ai_context", "")
    prompt = f"""
You are a Senior Data Analyst preparing an executive analysis.
Use only the following dataset context. Do not invent facts, numbers, trends, or causes.

DATASET CONTEXT:
{ai_context}

Return concise Markdown sections: Executive Summary, Key Findings, Strongest Areas,
Potential Problems, Business Recommendations, and Further Analysis. Clearly distinguish
facts from interpretations and say when information is insufficient.
"""
    return ask_llama(prompt)

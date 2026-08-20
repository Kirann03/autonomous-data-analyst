"""Neutral project configuration helpers shared by provider implementations."""

from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def load_project_environment() -> None:
    """Load the ignored project-root environment file without exposing values."""
    load_dotenv(PROJECT_ROOT / ".env")

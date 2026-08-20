"""Run a read-only PostgreSQL connectivity check using DATABASE_URL from .env."""

from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.engine.url import make_url
from sqlalchemy.exc import OperationalError, SQLAlchemyError


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from etl.load import get_database_url


def _safe_host(host: str | None) -> str:
    """Return a host only when it cannot contain URL-authority credential data."""
    if not host:
        return "unavailable"
    if "@" in host or any(character in host for character in ("#", "?", "/")):
        return "invalid URL authority (encode password URL-reserved characters)"
    return host


def _safe_postgres_message(message: str, host: str | None) -> str:
    """Prevent malformed URL authority content from being printed in DBAPI errors."""
    if host and _safe_host(host).startswith("invalid"):
        return message.replace(host, "[redacted malformed host]")
    return message


def main() -> int:
    parsed_url = None
    try:
        database_url = get_database_url()
        parsed_url = make_url(database_url)
        if parsed_url.get_backend_name() != "postgresql":
            print("PostgreSQL connection: FAIL")
            print(f"Configuration error: DATABASE_URL is configured for {parsed_url.get_backend_name()}, not PostgreSQL.")
            return 1

        engine = create_engine(database_url)
        try:
            with engine.connect() as connection:
                version = connection.execute(text("SELECT version();")).scalar_one()
                database = connection.execute(text("SELECT current_database();")).scalar_one()
        finally:
            engine.dispose()

        print("PostgreSQL connection: PASS")
        print(f"Database: {database}")
        print(f"Server version: {version}")
        return 0
    except OperationalError as error:
        print("PostgreSQL connection: FAIL")
        print(f"SQLAlchemy exception type: {error.__class__.__name__}")
        original = getattr(error, "orig", None)
        print(f"psycopg2 exception type: {original.__class__.__name__ if original else 'unavailable'}")
        print(f"pgcode: {getattr(original, 'pgcode', None) or 'unavailable'}")
        message = str(original) if original else str(error)
        print(f"PostgreSQL error message: {_safe_postgres_message(message, parsed_url.host if parsed_url else None)}")
        if parsed_url:
            print(f"Connection host: {_safe_host(parsed_url.host)}")
            print(f"Connection port: {parsed_url.port}")
            print(f"Database name: {parsed_url.database}")
            print(f"Username: {parsed_url.username}")
    except SQLAlchemyError as error:
        print("PostgreSQL connection: FAIL")
        print(f"SQLAlchemy exception type: {error.__class__.__name__}")
    except (ValueError, RuntimeError) as error:
        print("PostgreSQL connection: FAIL")
        print(f"Configuration error: {error}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

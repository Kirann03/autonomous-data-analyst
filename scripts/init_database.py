"""Initialize the local or PostgreSQL analytics database from the raw sales CSV."""

from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy.engine.url import make_url

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from etl.extract import extract_csv
from etl.load import get_database_url, load_transformed_sales, validate_database
from etl.transform import transform_dataframe


SOURCE_FILE = PROJECT_ROOT / "data" / "raw" / "sales.csv"


def main() -> None:
    database_url = get_database_url()
    parsed_url = make_url(database_url)
    source = extract_csv(SOURCE_FILE)
    transformed = transform_dataframe(source)
    table_counts = load_transformed_sales(transformed, database_url)
    validation = validate_database(database_url)

    print(f"Database type: {parsed_url.get_backend_name()}")
    print(f"Database URL: {parsed_url.render_as_string(hide_password=True)}")
    print(f"Rows loaded into fact_sales: {table_counts['fact_sales']}")
    print(f"Tables created: {', '.join(table_counts)}")
    print(f"Source rows: {len(source)}")
    for check, value in validation.items():
        print(f"{check}: {value}")


if __name__ == "__main__":
    main()

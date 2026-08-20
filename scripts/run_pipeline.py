"""Run the sales ETL pipeline from local CSV data or the configured S3 source."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from etl.pipeline import run_sales_pipeline


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the retail analytics ETL pipeline.")
    parser.add_argument("--source", choices=("local", "s3"), default="s3", help="Input source; defaults to S3.")
    args = parser.parse_args()
    try:
        result = run_sales_pipeline(args.source)
    except Exception as error:
        print(f"SOURCE: {'AWS S3' if args.source == 's3' else 'LOCAL CSV'}")
        print(f"STATUS: FAILED - {error}")
        return 1

    print(f"SOURCE: {'AWS S3' if result.source == 's3' else 'LOCAL CSV'}")
    print("OBJECT: raw/sales.csv" if result.source == "s3" else "FILE: data/raw/sales.csv")
    print(f"SOURCE ROWS: {result.source_rows}")
    print(f"TRANSFORMED ROWS: {result.transformed_rows}")
    print(f"LOADED ROWS: {result.loaded_rows}")
    print(f"DATABASE: {result.database_type.title()}")
    print(f"TOTAL REVENUE: {result.analytics['total_revenue']:.2f}")
    print(f"TOTAL PROFIT: {result.analytics['total_profit']:.2f}")
    print(f"PROFIT MARGIN: {result.analytics['overall_profit_margin']:.4f}%")
    print("STATUS: SUCCESS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

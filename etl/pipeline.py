"""Shared local and S3 sales-pipeline orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from math import isclose
from pathlib import Path

from sqlalchemy.engine.url import make_url

from etl.extract import extract_csv, extract_s3_csv
from etl.load import get_analytics_summary, get_database_url, load_transformed_sales, validate_database
from etl.transform import transform_sales_data


PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOCAL_SALES_FILE = PROJECT_ROOT / "data" / "raw" / "sales.csv"


class PipelineValidationError(RuntimeError):
    """Raised when a completed database load does not match its source."""


@dataclass(frozen=True)
class PipelineResult:
    source: str
    source_rows: int
    transformed_rows: int
    loaded_rows: int
    database_type: str
    validation: dict[str, int]
    analytics: dict[str, object]


def extract_sales_source(source: str):
    """Extract sales data from either the local development file or AWS S3."""
    if source == "local":
        return extract_csv(LOCAL_SALES_FILE)
    if source == "s3":
        return extract_s3_csv()
    raise ValueError("source must be either 'local' or 's3'.")


def run_sales_pipeline(source: str = "s3", database_url: str | None = None) -> PipelineResult:
    """Extract, transform, load, and validate a sales dataset from the selected source."""
    source_data = extract_sales_source(source)
    transformed_data = transform_sales_data(source_data)
    resolved_url = get_database_url(database_url)
    loaded_tables = load_transformed_sales(transformed_data, resolved_url)
    validation = validate_database(resolved_url)
    if validation["loaded_orders"] != len(source_data):
        raise PipelineValidationError("Loaded order count does not match source row count.")
    if any(validation[name] for name in ("duplicate_order_ids", "important_nulls", "unreasonable_metrics", "invalid_foreign_keys")):
        raise PipelineValidationError("Database validation failed; inspect the validation report.")
    return PipelineResult(
        source=source,
        source_rows=len(source_data),
        transformed_rows=len(transformed_data),
        loaded_rows=loaded_tables["fact_sales"],
        database_type=make_url(resolved_url).get_backend_name(),
        validation=validation,
        analytics=get_analytics_summary(resolved_url),
    )


def compare_pipeline_results(left: PipelineResult, right: PipelineResult, *, tolerance: float = 1e-6) -> list[str]:
    """Return analytical differences between two pipeline runs, using numeric tolerance."""
    differences = []
    for metric in ("unique_orders", "unique_customers", "unique_products", "total_quantity"):
        if left.analytics[metric] != right.analytics[metric]:
            differences.append(metric)
    for metric in ("total_revenue", "total_profit", "overall_profit_margin"):
        if not isclose(float(left.analytics[metric]), float(right.analytics[metric]), rel_tol=tolerance, abs_tol=tolerance):
            differences.append(metric)
    regions = set(left.analytics["revenue_by_region"]) | set(right.analytics["revenue_by_region"])
    for region in regions:
        left_value = left.analytics["revenue_by_region"].get(region, 0)
        right_value = right.analytics["revenue_by_region"].get(region, 0)
        if not isclose(float(left_value), float(right_value), rel_tol=tolerance, abs_tol=tolerance):
            differences.append(f"revenue_by_region.{region}")
    return differences

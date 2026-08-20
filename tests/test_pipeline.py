import pandas as pd
import pytest

from etl import pipeline
from etl.extract import extract_s3_csv
from etl.transform import transform_sales_data


def test_extract_s3_csv_uses_configured_bucket(monkeypatch):
    expected = pd.DataFrame({"order_id": ["ORD1"]})
    config = type("Config", (), {"bucket_name": "project-bucket"})()
    client = object()
    monkeypatch.setattr("etl.extract.load_s3_config", lambda: config)
    monkeypatch.setattr("etl.extract.read_csv_from_s3", lambda actual_client, bucket, key: expected)

    result = extract_s3_csv("raw/sales.csv", client=client)

    pd.testing.assert_frame_equal(result, expected)


def test_source_selection_uses_requested_extractor(monkeypatch):
    local = pd.DataFrame({"source": ["local"]})
    s3 = pd.DataFrame({"source": ["s3"]})
    monkeypatch.setattr(pipeline, "extract_csv", lambda path: local)
    monkeypatch.setattr(pipeline, "extract_s3_csv", lambda: s3)

    assert pipeline.extract_sales_source("local").iloc[0, 0] == "local"
    assert pipeline.extract_sales_source("s3").iloc[0, 0] == "s3"


def test_local_and_s3_data_use_identical_transformation():
    raw = pd.DataFrame({"Order ID": ["ORD1"], "Order Date": ["01-01-2025"], "Quantity": [2], "Unit Price": [10], "Cost": [6], "Discount": [0.1]})
    pd.testing.assert_frame_equal(transform_sales_data(raw.copy()), transform_sales_data(raw.copy()))


def test_pipeline_fails_when_loaded_rows_do_not_match_source(monkeypatch):
    source = pd.DataFrame({"order_id": ["ORD1", "ORD2"]})
    monkeypatch.setattr(pipeline, "extract_sales_source", lambda selected: source)
    monkeypatch.setattr(pipeline, "transform_sales_data", lambda data: data)
    monkeypatch.setattr(pipeline, "get_database_url", lambda url: "sqlite:///:memory:")
    monkeypatch.setattr(pipeline, "load_transformed_sales", lambda data, url: {"fact_sales": 2})
    monkeypatch.setattr(pipeline, "validate_database", lambda url: {"loaded_orders": 1, "duplicate_order_ids": 0, "important_nulls": 0, "unreasonable_metrics": 0, "invalid_foreign_keys": 0})

    with pytest.raises(pipeline.PipelineValidationError, match="Loaded order count"):
        pipeline.run_sales_pipeline("local")


def test_pipeline_comparison_uses_numeric_tolerance():
    result_type = pipeline.PipelineResult
    analytics = {"unique_orders": 1, "unique_customers": 1, "unique_products": 1, "total_quantity": 2, "total_revenue": 10.0, "total_profit": 4.0, "overall_profit_margin": 40.0, "revenue_by_region": {"North": 10.0}}
    local = result_type("local", 1, 1, 1, "sqlite", {}, analytics)
    cloud = result_type("s3", 1, 1, 1, "sqlite", {}, {**analytics, "total_revenue": 10.00000001, "revenue_by_region": {"North": 10.00000001}})
    assert pipeline.compare_pipeline_results(local, cloud) == []

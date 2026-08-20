import pandas as pd

from src.data_query_engine import query_dataset


def _sales_frame():
    return pd.DataFrame({
        "region": ["North", "South", "East", "West"],
        "profit": [300, 450, 100, 360],
        "revenue": [1000, 1500, 700, 1200],
    })


def test_highest_profit_preserves_region_and_value():
    answer = query_dataset(_sales_frame(), "Which region has the highest profit?")
    assert "South" in answer and "450.00" in answer


def test_lowest_profit_preserves_region_and_value():
    answer = query_dataset(_sales_frame(), "Which region has the lowest profit?")
    assert "East" in answer and "100.00" in answer


def test_highest_revenue_preserves_region_and_value():
    answer = query_dataset(_sales_frame(), "Which region has the highest revenue?")
    assert "South" in answer and "1,500.00" in answer

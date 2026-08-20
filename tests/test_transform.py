import pandas as pd
import pytest

from etl.transform import calculate_kpis, convert_numeric_columns, remove_duplicates, transform_dataframe


def test_remove_duplicates():
    result = remove_duplicates(pd.DataFrame({"product": ["Widget", "Widget", "Gadget"]}))
    assert result["product"].tolist() == ["Widget", "Gadget"]


def test_convert_numeric_columns_handles_currency_text():
    result = convert_numeric_columns(pd.DataFrame({"quantity": ["2"], "price": ["$12.50"]}))
    assert result.loc[0, "quantity"] == 2
    assert result.loc[0, "price"] == 12.5


def test_calculate_revenue_profit_and_margin():
    result = calculate_kpis(pd.DataFrame({"quantity": [2], "price": [15], "cost": [9]}))
    assert result.loc[0, "revenue"] == 30
    assert result.loc[0, "profit"] == 12
    assert result.loc[0, "profit_margin"] == 40


def test_calculate_kpis_applies_discount_to_revenue():
    result = calculate_kpis(pd.DataFrame({"quantity": [2], "price": [15], "cost": [9], "discount": [0.1]}))
    assert result.loc[0, "revenue"] == 27
    assert result.loc[0, "profit"] == 9
    assert round(result.loc[0, "profit_margin"], 2) == 33.33


def test_transform_rejects_negative_prices():
    with pytest.raises(ValueError, match="Price values cannot be negative"):
        transform_dataframe(pd.DataFrame({"quantity": [1], "price": [-1], "cost": [0]}))

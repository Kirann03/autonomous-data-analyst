"""Composable cleaning and KPI transformation functions for sales data."""

from __future__ import annotations

import re
from collections.abc import Iterable

import numpy as np
import pandas as pd


COLUMN_ALIASES = {
    "units": "quantity",
    "qty": "quantity",
    "unit_price": "price",
    "selling_price": "price",
    "sales_price": "price",
    "unit_cost": "cost",
    "cost_price": "cost",
}
NUMERIC_COLUMNS = ("quantity", "price", "cost", "discount", "sales_target")


def standardize_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy with lowercase, snake_case column names and known aliases."""
    result = df.copy()
    columns = []
    for column in result.columns:
        name = re.sub(r"[^a-z0-9]+", "_", str(column).strip().lower())
        name = re.sub(r"_+", "_", name).strip("_")
        columns.append(COLUMN_ALIASES.get(name, name))
    if len(columns) != len(set(columns)):
        raise ValueError("Column standardization produced duplicate column names.")
    result.columns = columns
    return result


def normalize_missing_values(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize blank text to missing values without inventing business data."""
    result = df.copy()
    for column in result.select_dtypes(include=["object", "string"]).columns:
        result[column] = result[column].astype("string").str.strip()
        result[column] = result[column].replace({"": pd.NA, "nan": pd.NA, "none": pd.NA})
    return result


def remove_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    """Remove duplicate rows and reset the row index."""
    return df.drop_duplicates().reset_index(drop=True)


def convert_date_columns(df: pd.DataFrame, date_columns: Iterable[str] | None = None) -> pd.DataFrame:
    """Convert named or date-like columns to datetimes, coercing invalid values."""
    result = df.copy()
    columns = date_columns or [column for column in result.columns if "date" in column]
    for column in columns:
        if column in result.columns:
            result[column] = pd.to_datetime(result[column], errors="coerce", dayfirst=True)
    return result


def convert_numeric_columns(
    df: pd.DataFrame, numeric_columns: Iterable[str] = NUMERIC_COLUMNS
) -> pd.DataFrame:
    """Convert common business numeric fields, including currency-formatted text."""
    result = df.copy()
    for column in numeric_columns:
        if column in result.columns:
            cleaned = result[column].astype("string").str.replace(r"[^0-9.\-]", "", regex=True)
            result[column] = pd.to_numeric(cleaned, errors="coerce")
    return result


def validate_quantities_and_prices(df: pd.DataFrame) -> pd.DataFrame:
    """Reject invalid quantities, monetary values, and discount rates."""
    for column in ("quantity", "price", "cost", "sales_target"):
        if column in df.columns and (df[column].dropna() < 0).any():
            raise ValueError(f"{column.capitalize()} values cannot be negative.")
    if "discount" in df.columns and (
        (df["discount"].dropna() < 0) | (df["discount"].dropna() > 1)
    ).any():
        raise ValueError("Discount values must be between 0 and 1.")
    return df


def calculate_kpis(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate revenue, profit, and percentage profit margin when inputs exist."""
    result = df.copy()
    if not {"quantity", "price", "cost"}.issubset(result.columns):
        return result
    discount = result["discount"].fillna(0) if "discount" in result.columns else 0
    result["revenue"] = result["quantity"] * result["price"] * (1 - discount)
    result["profit"] = result["revenue"] - (result["quantity"] * result["cost"])
    result["profit_margin"] = np.where(
        result["revenue"].notna() & result["revenue"].ne(0),
        result["profit"] / result["revenue"] * 100,
        np.nan,
    )
    return result


def transform_sales_data(df: pd.DataFrame) -> pd.DataFrame:
    """Apply the standard reusable cleaning and sales-KPI transformation pipeline."""
    result = standardize_column_names(df)
    result = normalize_missing_values(result)
    result = remove_duplicates(result)
    result = convert_date_columns(result)
    result = convert_numeric_columns(result)
    result = validate_quantities_and_prices(result)
    return calculate_kpis(result)


def transform_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Backward-compatible alias for :func:`transform_sales_data`."""
    return transform_sales_data(df)

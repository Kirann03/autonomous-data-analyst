"""Idempotent SQLAlchemy loading for the retail sales star schema."""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import Column, Date, ForeignKey, Index, Integer, MetaData, Numeric, String, Table, create_engine, delete, func, select, text
from sqlalchemy.engine import Engine
from sqlalchemy.engine.url import make_url


PROJECT_ROOT = Path(__file__).resolve().parents[1]


metadata = MetaData()
dim_customer = Table("dim_customer", metadata, Column("customer_id", String(50), primary_key=True))
dim_product = Table(
    "dim_product", metadata, Column("product_id", String(50), primary_key=True),
    Column("product_name", String(255), nullable=False), Column("category", String(100), nullable=False),
)
dim_region = Table(
    "dim_region", metadata, Column("region_key", Integer, primary_key=True),
    Column("region", String(50), nullable=False), Column("state", String(100), nullable=False),
)
dim_date = Table(
    "dim_date", metadata, Column("date_key", Integer, primary_key=True),
    Column("full_date", Date, nullable=False, unique=True), Column("year", Integer, nullable=False),
    Column("month_number", Integer, nullable=False), Column("month_name", String(20), nullable=False),
)
fact_sales = Table(
    "fact_sales", metadata, Column("order_id", String(50), primary_key=True),
    Column("date_key", Integer, ForeignKey("dim_date.date_key"), nullable=False),
    Column("customer_id", String(50), ForeignKey("dim_customer.customer_id"), nullable=False),
    Column("product_id", String(50), ForeignKey("dim_product.product_id"), nullable=False),
    Column("region_key", Integer, ForeignKey("dim_region.region_key"), nullable=False),
    Column("quantity", Integer, nullable=False), Column("unit_price", Numeric(18, 2), nullable=False),
    Column("cost", Numeric(18, 2), nullable=False), Column("discount", Numeric(8, 4), nullable=False),
    Column("sales_target", Numeric(18, 2), nullable=False), Column("revenue", Numeric(18, 6), nullable=False),
    Column("profit", Numeric(18, 6), nullable=False), Column("profit_margin", Numeric(12, 6), nullable=False),
)
Index("idx_fact_sales_date_key", fact_sales.c.date_key)
Index("idx_fact_sales_product_id", fact_sales.c.product_id)
Index("idx_fact_sales_region_key", fact_sales.c.region_key)
Index("idx_dim_region_region_state", dim_region.c.region, dim_region.c.state, unique=True)

REQUIRED_COLUMNS = {
    "order_id", "order_date", "customer_id", "product_id", "product_name", "category", "region", "state",
    "quantity", "price", "cost", "discount", "sales_target", "revenue", "profit", "profit_margin",
}


def get_database_url(database_url: str | None = None) -> str:
    """Return an explicit URL or DATABASE_URL from the environment."""
    load_dotenv(PROJECT_ROOT / ".env")
    url = database_url or os.getenv("DATABASE_URL")
    if not url:
        raise ValueError("DATABASE_URL must be set before initializing the database.")
    return url


def create_database_engine(database_url: str | None = None) -> Engine:
    """Create an engine compatible with SQLite locally and PostgreSQL in production."""
    url = get_database_url(database_url)
    parsed_url = make_url(url)
    if parsed_url.get_backend_name() == "sqlite" and parsed_url.database not in (None, ":memory:"):
        database_path = Path(parsed_url.database).expanduser()
        database_path.parent.mkdir(parents=True, exist_ok=True)
    return create_engine(url)


def create_schema(engine: Engine) -> None:
    """Create all fact and dimension tables if they do not already exist."""
    metadata.create_all(engine)
    if engine.dialect.name == "postgresql":
        # Preserve calculated KPI precision so PostgreSQL totals match the shared ETL output.
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE fact_sales ALTER COLUMN revenue TYPE NUMERIC(18, 6)"))
            connection.execute(text("ALTER TABLE fact_sales ALTER COLUMN profit TYPE NUMERIC(18, 6)"))
            connection.execute(text("ALTER TABLE fact_sales ALTER COLUMN profit_margin TYPE NUMERIC(12, 6)"))


def _validate_input(df: pd.DataFrame) -> None:
    missing = REQUIRED_COLUMNS.difference(df.columns)
    if missing:
        raise ValueError(f"Transformed dataset is missing columns: {', '.join(sorted(missing))}")
    if df["order_id"].isna().any() or df["order_id"].duplicated().any():
        raise ValueError("order_id must be present and unique before database loading.")


def _build_tables(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Create dimension and fact DataFrames from the transformed sales data."""
    _validate_input(df)
    sales = df.copy()
    sales["order_date"] = pd.to_datetime(sales["order_date"], errors="raise")
    conflicts = sales.groupby("product_id")[["product_name", "category"]].nunique()
    if (conflicts > 1).any().any():
        raise ValueError("Each product_id must map to one product name and category.")

    customers = sales[["customer_id"]].drop_duplicates().sort_values("customer_id")
    products = sales[["product_id", "product_name", "category"]].drop_duplicates().sort_values("product_id")
    regions = sales[["region", "state"]].drop_duplicates().sort_values(["region", "state"]).reset_index(drop=True)
    regions.insert(0, "region_key", regions.index + 1)
    dates = sales[["order_date"]].drop_duplicates().sort_values("order_date").copy()
    dates["date_key"] = dates["order_date"].dt.strftime("%Y%m%d").astype(int)
    dates["full_date"] = dates["order_date"].dt.date
    dates["year"] = dates["order_date"].dt.year
    dates["month_number"] = dates["order_date"].dt.month
    dates["month_name"] = dates["order_date"].dt.month_name()
    dates = dates[["date_key", "full_date", "year", "month_number", "month_name"]]

    facts = sales.merge(regions, on=["region", "state"], how="left", validate="many_to_one")
    facts["date_key"] = facts["order_date"].dt.strftime("%Y%m%d").astype(int)
    facts = facts[["order_id", "date_key", "customer_id", "product_id", "region_key", "quantity", "price", "cost", "discount", "sales_target", "revenue", "profit", "profit_margin"]]
    facts = facts.rename(columns={"price": "unit_price"})
    return {"dim_customer": customers, "dim_product": products, "dim_region": regions, "dim_date": dates, "fact_sales": facts}


def load_transformed_sales(df: pd.DataFrame, database_url: str | None = None) -> dict[str, int]:
    """Replace warehouse content in one transaction, preventing duplicate reruns."""
    tables = _build_tables(df)
    engine = create_database_engine(database_url)
    try:
        create_schema(engine)
        with engine.begin() as connection:
            if engine.dialect.name == "sqlite":
                connection.execute(text("PRAGMA foreign_keys = ON"))
            for table in (fact_sales, dim_date, dim_region, dim_product, dim_customer):
                connection.execute(delete(table))
            for table_name in ("dim_customer", "dim_product", "dim_region", "dim_date", "fact_sales"):
                tables[table_name].to_sql(table_name, connection, if_exists="append", index=False)
        return {name: len(table) for name, table in tables.items()}
    finally:
        engine.dispose()


def validate_database(database_url: str | None = None) -> dict[str, int]:
    """Return concise checks for a completed load."""
    engine = create_database_engine(database_url)
    try:
        with engine.connect() as connection:
            result = {
                "loaded_orders": connection.scalar(select(func.count()).select_from(fact_sales)) or 0,
                "duplicate_order_ids": connection.scalar(text("SELECT COUNT(*) FROM (SELECT order_id FROM fact_sales GROUP BY order_id HAVING COUNT(*) > 1)")) or 0,
                "important_nulls": connection.scalar(text("SELECT COUNT(*) FROM fact_sales WHERE order_id IS NULL OR date_key IS NULL OR customer_id IS NULL OR product_id IS NULL OR region_key IS NULL OR quantity IS NULL OR unit_price IS NULL OR revenue IS NULL OR profit IS NULL OR profit_margin IS NULL")) or 0,
                "unreasonable_metrics": connection.scalar(text("SELECT COUNT(*) FROM fact_sales WHERE revenue < 0 OR profit_margin < -100 OR profit_margin > 100")) or 0,
                "invalid_foreign_keys": connection.scalar(text("SELECT COUNT(*) FROM fact_sales f LEFT JOIN dim_customer c ON f.customer_id = c.customer_id LEFT JOIN dim_product p ON f.product_id = p.product_id LEFT JOIN dim_region r ON f.region_key = r.region_key LEFT JOIN dim_date d ON f.date_key = d.date_key WHERE c.customer_id IS NULL OR p.product_id IS NULL OR r.region_key IS NULL OR d.date_key IS NULL")) or 0,
            }
        return {key: int(value) for key, value in result.items()}
    finally:
        engine.dispose()


def get_analytics_summary(database_url: str | None = None) -> dict[str, object]:
    """Return database-level KPI results used to compare local and S3 pipeline runs."""
    engine = create_database_engine(database_url)
    try:
        with engine.connect() as connection:
            totals = connection.execute(text("""
                SELECT COUNT(*) AS unique_orders,
                       COUNT(DISTINCT customer_id) AS unique_customers,
                       COUNT(DISTINCT product_id) AS unique_products,
                       COALESCE(SUM(quantity), 0) AS total_quantity,
                       COALESCE(SUM(revenue), 0) AS total_revenue,
                       COALESCE(SUM(profit), 0) AS total_profit
                FROM fact_sales
            """)).mappings().one()
            regions = connection.execute(text("""
                SELECT r.region, COALESCE(SUM(f.revenue), 0) AS revenue
                FROM fact_sales f
                JOIN dim_region r ON f.region_key = r.region_key
                GROUP BY r.region
                ORDER BY r.region
            """)).mappings().all()
        revenue = float(totals["total_revenue"])
        profit = float(totals["total_profit"])
        return {
            "unique_orders": int(totals["unique_orders"]),
            "unique_customers": int(totals["unique_customers"]),
            "unique_products": int(totals["unique_products"]),
            "total_quantity": int(totals["total_quantity"]),
            "total_revenue": revenue,
            "total_profit": profit,
            "overall_profit_margin": (profit / revenue * 100) if revenue else None,
            "revenue_by_region": {row["region"]: float(row["revenue"]) for row in regions},
        }
    finally:
        engine.dispose()

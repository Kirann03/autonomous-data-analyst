-- Star-schema-inspired retail model. fact_sales is one row per source Order_ID.
-- VARCHAR keys preserve the source identifiers rather than inventing surrogate IDs.

CREATE TABLE IF NOT EXISTS dim_customer (
    customer_id VARCHAR(50) PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS dim_product (
    product_id VARCHAR(50) PRIMARY KEY,
    product_name VARCHAR(255) NOT NULL,
    category VARCHAR(100) NOT NULL
);

-- State is retained with its parent region because the source has no separate state attributes.
CREATE TABLE IF NOT EXISTS dim_region (
    region_key INTEGER PRIMARY KEY,
    region VARCHAR(50) NOT NULL,
    state VARCHAR(100) NOT NULL,
    UNIQUE (region, state)
);

CREATE TABLE IF NOT EXISTS dim_date (
    date_key INTEGER PRIMARY KEY, -- YYYYMMDD, e.g. 20250818
    full_date DATE NOT NULL UNIQUE,
    year INTEGER NOT NULL,
    month_number INTEGER NOT NULL,
    month_name VARCHAR(20) NOT NULL
);

CREATE TABLE IF NOT EXISTS fact_sales (
    order_id VARCHAR(50) PRIMARY KEY,
    date_key INTEGER NOT NULL REFERENCES dim_date(date_key),
    customer_id VARCHAR(50) NOT NULL REFERENCES dim_customer(customer_id),
    product_id VARCHAR(50) NOT NULL REFERENCES dim_product(product_id),
    region_key INTEGER NOT NULL REFERENCES dim_region(region_key),
    quantity INTEGER NOT NULL,
    unit_price NUMERIC(18, 2) NOT NULL,
    cost NUMERIC(18, 2) NOT NULL,
    discount NUMERIC(8, 4) NOT NULL, -- decimal rate, not a percentage string
    sales_target NUMERIC(18, 2) NOT NULL,
    -- Calculated values retain six decimals to prevent row-level rounding from changing KPI totals.
    revenue NUMERIC(18, 6) NOT NULL, -- quantity * unit_price * (1 - discount)
    profit NUMERIC(18, 6) NOT NULL, -- revenue - (quantity * cost)
    profit_margin NUMERIC(12, 6) NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_fact_sales_date_key ON fact_sales (date_key);
CREATE INDEX IF NOT EXISTS idx_fact_sales_product_id ON fact_sales (product_id);
CREATE INDEX IF NOT EXISTS idx_fact_sales_region_key ON fact_sales (region_key);
CREATE INDEX IF NOT EXISTS idx_dim_region_region_state ON dim_region (region, state);

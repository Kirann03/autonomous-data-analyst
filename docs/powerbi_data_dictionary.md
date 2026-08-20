# Power BI Data Dictionary

Source database: `data/analytics.db` (SQLite). Import the five warehouse tables, not the raw CSV.

## Model classification

| Table | Role | Rows | Power BI use |
|---|---|---:|---|
| `fact_sales` | Fact | 50,000 | Transaction-level measures and visuals |
| `dim_date` | Dimension / date table | 383 | Time slicing, trends, time intelligence |
| `dim_customer` | Dimension | 4,000 | Customer filtering and customer KPIs |
| `dim_product` | Dimension | 34 | Product and category analysis |
| `dim_region` | Dimension | 16 | Region and state analysis |

## `fact_sales` — fact table

One row represents one source `order_id`.

| Column | SQLite type | Business meaning | Example | Power BI usage |
|---|---|---|---|---|
| `order_id` | VARCHAR(50) | Unique sales order identifier; primary key | `ORD100000` | Order count and drill-through ID |
| `date_key` | INTEGER | Date foreign key in `YYYYMMDD` form | `20250415` | Relationship to `dim_date` |
| `customer_id` | VARCHAR(50) | Customer foreign key | `C100271` | Relationship to `dim_customer` |
| `product_id` | VARCHAR(50) | Product foreign key | `P1022` | Relationship to `dim_product` |
| `region_key` | INTEGER | Region/state foreign key | `8` | Relationship to `dim_region` |
| `quantity` | INTEGER | Units sold | `1` | Sum measure, product volume |
| `unit_price` | NUMERIC(18,2) | Pre-discount selling price per unit | `24954.46` | Average unit price measure |
| `cost` | NUMERIC(18,2) | Unit cost | `16308.55` | Cost/profit analysis |
| `discount` | NUMERIC(8,4) | Discount rate stored as decimal | `0.027` | Percentage measure and discount analysis |
| `sales_target` | NUMERIC(18,2) | Target associated with the sales row | `56160.93` | Target and achievement measures |
| `revenue` | NUMERIC(18,2) | Net sales after discount | `24280.68958` | Primary revenue measure |
| `profit` | NUMERIC(18,2) | Net revenue minus quantity × unit cost | `7972.13958` | Primary profit measure |
| `profit_margin` | NUMERIC(9,4) | Row-level profit / revenue × 100 | `32.83325` | Detail inspection only; use weighted measure for totals |

## `dim_date` — date dimension

| Column | SQLite type | Business meaning | Example | Power BI usage |
|---|---|---|---|---|
| `date_key` | INTEGER | Date primary key in `YYYYMMDD` form | `20250415` | Relationship key; hide in report view |
| `full_date` | DATE | Calendar date | `2025-04-15` | Mark this table as date table using this column |
| `year` | INTEGER | Calendar year | `2025` | Year slicer/axis |
| `month_number` | INTEGER | Month ordering number | `4` | Sort `month_name` by this column |
| `month_name` | VARCHAR(20) | Calendar month name | `April` | Month slicer/axis |

## `dim_customer` — customer dimension

| Column | SQLite type | Business meaning | Example | Power BI usage |
|---|---|---|---|---|
| `customer_id` | VARCHAR(50) | Unique customer identifier; primary key | `C100271` | Customer slicer, top-customer visuals |

## `dim_product` — product dimension

| Column | SQLite type | Business meaning | Example | Power BI usage |
|---|---|---|---|---|
| `product_id` | VARCHAR(50) | Product identifier; primary key | `P1022` | Relationship key; hide in report view |
| `product_name` | VARCHAR(255) | Product display name | `Sofa Set 3-Seater` | Product rankings and detail visuals |
| `category` | VARCHAR(100) | Product category | `Furniture` | Category slicer and charts |

## `dim_region` — geography dimension

| Column | SQLite type | Business meaning | Example | Power BI usage |
|---|---|---|---|---|
| `region_key` | INTEGER | Region/state primary key | `8` | Relationship key; hide in report view |
| `region` | VARCHAR(50) | Sales region | `North` | Regional slicer and charts |
| `state` | VARCHAR(100) | State within the region | `Uttar Pradesh` | State drill-down and map/table visuals |

Important fields: treat `revenue`, `profit`, `quantity`, `sales_target`, `cost`, and `unit_price` as numeric fields; `discount` and KPI margins as percentages; IDs as text/integer keys; and product/category/region/state/month as categorical attributes.

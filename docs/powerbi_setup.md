# Power BI Desktop Setup

## Connect to SQLite

The reporting source is the SQLite database at:

```text
D:\PU\Lang\Python\Project\AI_Data_Analyst\data\analytics.db
```

Do not connect Power BI to `data/raw/sales.csv`. The database already contains transformed measures and dimension tables.

Power BI Desktop does not ship a dedicated SQLite connector. Install a SQLite-compatible ODBC driver whose architecture matches Power BI Desktop (normally 64-bit), then create an ODBC DSN that points to `analytics.db`. In Power BI Desktop select **Get data** → **ODBC**, choose the DSN, and import:

- `fact_sales`
- `dim_customer`
- `dim_product`
- `dim_region`
- `dim_date`

Alternatively, the ODBC connector accepts a DSN or driver connection string when supported by the installed driver. Follow the driver provider's connection-string syntax. Microsoft documents DSN and driver connection-string use for the ODBC connector. [Power Query ODBC connector](https://learn.microsoft.com/en-us/power-query/connectors/odbc)

## Recommended model configuration

Use **Import** storage mode for this 50,000-row local SQLite dataset. Import stores a snapshot in the model and provides fast visual interaction; refresh is needed to retrieve later ETL output. [Power BI storage modes](https://learn.microsoft.com/en-us/power-bi/transform-model/desktop-storage-mode)

Create these active, one-to-many, single-direction relationships. The filter must flow from each dimension to `fact_sales`.

| From (one side) | To (many side) | Cross-filter direction |
|---|---|---|
| `dim_date[date_key]` | `fact_sales[date_key]` | Single: `dim_date` → `fact_sales` |
| `dim_customer[customer_id]` | `fact_sales[customer_id]` | Single: `dim_customer` → `fact_sales` |
| `dim_product[product_id]` | `fact_sales[product_id]` | Single: `dim_product` → `fact_sales` |
| `dim_region[region_key]` | `fact_sales[region_key]` | Single: `dim_region` → `fact_sales` |

Hide the technical relationship keys from report view after relationships are verified: fact foreign keys and the dimension key columns. Keep meaningful descriptive fields visible.

## Date table setup

1. In Power Query, set `dim_date[full_date]` to **Date** and `dim_date[date_key]` to **Whole number**.
2. In Model view, select `dim_date` and choose **Mark as date table** using `full_date`.
3. Set `dim_date[month_name]` to sort by `dim_date[month_number]`.

`full_date` is unique and non-null in the inspected database. Power BI validates date-table columns for uniqueness, no nulls, and contiguous dates when a table is marked. [Set and use date tables](https://learn.microsoft.com/en-us/power-bi/transform-model/desktop-date-tables)

## Refresh considerations

Run the ETL pipeline before refreshing Power BI:

```powershell
python scripts/run_pipeline.py --source s3
```

Then choose **Refresh** in Power BI Desktop. Because SQLite is a local file source, scheduled refresh after publishing generally requires an accessible gateway/driver on the refresh machine. Reopen or refresh the report after a successful ETL load; do not overwrite or manually edit `analytics.db` while Power BI is refreshing it.

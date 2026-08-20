# Power BI Data Quality Checks

The verified ETL validation for the current 50,000-row database reported:

| Check | Result | Interpretation |
|---|---:|---|
| Loaded orders | 50,000 | Matches the source row count |
| Duplicate `order_id` | 0 | No duplicate sales orders |
| Important fact-table nulls | 0 | Required fact fields are populated |
| Unreasonable metrics | 0 | No negative revenue; all margins are between -100% and 100% |
| Invalid foreign keys | 0 | No orphan dimension references |

Use these checks after every pipeline run. They can be placed on a hidden Power BI quality page or performed with a source query before import.

| Quality rule | Field(s) | Expected result | Notes |
|---|---|---|---|
| Duplicate order check | `fact_sales[order_id]` | Count equals distinct count | `order_id` is the fact primary key |
| Missing order date check | `fact_sales[date_key]`, `dim_date[full_date]` | Zero blanks | `fact_sales` does not contain `order_date`; use the date relationship |
| Missing customer check | `fact_sales[customer_id]` | Zero blanks | Also confirm it resolves to `dim_customer` |
| Missing product check | `fact_sales[product_id]` | Zero blanks | Also confirm it resolves to `dim_product` |
| Negative quantity check | `fact_sales[quantity]` | Zero rows | Quantity is expected to be non-negative |
| Negative revenue check | `fact_sales[revenue]` | Zero rows | Revenue after discount should not be negative |
| Invalid discount check | `fact_sales[discount]` | All values from 0 to 1 | Stored as decimal rate; format as percentage in Power BI |
| Invalid profit check | `fact_sales[profit]` | Investigate only outside business thresholds | Negative profit is allowed and can represent a loss |
| Margin range check | `fact_sales[profit_margin]` | -100% to 100% | Existing ETL validation applies this range |
| Orphan-key check | Four fact foreign keys | Zero rows | Check all dimension relationships |

Recommended report-level DAX diagnostics:

```DAX
Duplicate Order Rows =
COUNTROWS ( fact_sales ) - DISTINCTCOUNT ( fact_sales[order_id] )

Missing Customer IDs =
COUNTROWS ( FILTER ( fact_sales, ISBLANK ( fact_sales[customer_id] ) ) )

Invalid Discount Rows =
COUNTROWS (
    FILTER ( fact_sales, fact_sales[discount] < 0 || fact_sales[discount] > 1 )
)

Negative Revenue Rows =
COUNTROWS ( FILTER ( fact_sales, fact_sales[revenue] < 0 ) )
```

These measures should evaluate to zero for the current load. For orphan foreign keys, rely on relationship integrity in the source validation; Power BI's standard model relationship does not by itself expose a simple universal orphan-count measure.

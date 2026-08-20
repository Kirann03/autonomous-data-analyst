# Power BI KPI Specification

All KPI measures are calculated from `fact_sales`. Use measures, not pre-aggregated values. Currency formatting should use the report currency convention; percentage measures use one or two decimal places.

| KPI | Business definition | Formula / source columns | Recommended DAX measure | Format |
|---|---|---|---|---|
| Revenue | Net sales after discounts | `SUM(fact_sales[revenue])` | `[Revenue]` | Currency, 2 decimals |
| Profit | Net revenue after product costs | `SUM(fact_sales[profit])` | `[Profit]` | Currency, 2 decimals |
| Profit Margin | Weighted profitability of selected sales | `[Profit] / [Revenue]` | `[Profit Margin]` | Percentage, 2 decimals |
| Total Orders | Count of unique orders | `DISTINCTCOUNT(fact_sales[order_id])` | `[Total Orders]` | Whole number |
| Total Quantity | Units sold | `SUM(fact_sales[quantity])` | `[Total Quantity]` | Whole number |
| Average Order Value | Average net revenue per unique order | `[Revenue] / [Total Orders]` | `[Average Order Value]` | Currency, 2 decimals |
| Average Unit Price | Quantity-weighted selling price before discount | `SUMX(quantity × unit_price) / SUM(quantity)` | `[Average Unit Price]` | Currency, 2 decimals |
| Total Customers | Customers with sales in current filter context | `DISTINCTCOUNT(fact_sales[customer_id])` | `[Total Customers]` | Whole number |
| Total Products | Products sold in current filter context | `DISTINCTCOUNT(fact_sales[product_id])` | `[Total Products]` | Whole number |
| Discount % | Quantity-weighted discount rate | `SUMX(quantity × discount) / SUM(quantity)` | `[Discount %]` | Percentage, 2 decimals |
| Sales Target | Sum of row-level targets | `SUM(fact_sales[sales_target])` | `[Sales Target]` | Currency, 2 decimals |
| Target Achievement % | Actual revenue relative to target | `[Revenue] / [Sales Target]` | `[Target Achievement %]` | Percentage, 2 decimals |

`fact_sales[profit_margin]` is a valid row-level diagnostic field, but do not average it for executive KPIs. The weighted `[Profit Margin]` measure is the correct aggregate.

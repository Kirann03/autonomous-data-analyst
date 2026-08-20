# Power BI DAX Measures

Create these measures in `fact_sales`. The expressions use only columns verified in `analytics.db`.

```DAX
Revenue =
SUM ( fact_sales[revenue] )

Profit =
SUM ( fact_sales[profit] )

Profit Margin =
DIVIDE ( [Profit], [Revenue] )

Total Orders =
DISTINCTCOUNT ( fact_sales[order_id] )

Total Quantity =
SUM ( fact_sales[quantity] )

Average Order Value =
DIVIDE ( [Revenue], [Total Orders] )

Average Unit Price =
DIVIDE (
    SUMX ( fact_sales, fact_sales[quantity] * fact_sales[unit_price] ),
    [Total Quantity]
)

Total Customers =
DISTINCTCOUNT ( fact_sales[customer_id] )

Total Products =
DISTINCTCOUNT ( fact_sales[product_id] )

Discount % =
DIVIDE (
    SUMX ( fact_sales, fact_sales[quantity] * fact_sales[discount] ),
    [Total Quantity]
)

Sales Target =
SUM ( fact_sales[sales_target] )

Target Achievement % =
DIVIDE ( [Revenue], [Sales Target] )

Customer Order Frequency =
DIVIDE ( [Total Orders], [Total Customers] )

Revenue Variance to Target =
[Revenue] - [Sales Target]
```

Format `Revenue`, `Profit`, `Average Order Value`, `Average Unit Price`, `Sales Target`, and `Revenue Variance to Target` as currency. Format `Profit Margin`, `Discount %`, and `Target Achievement %` as percentage. Format order, quantity, customer, product, and frequency measures as whole numbers or decimals as appropriate.

For time visuals, use `dim_date[full_date]` as the axis and set `dim_date[month_name]` to **Sort by column** → `dim_date[month_number]`.

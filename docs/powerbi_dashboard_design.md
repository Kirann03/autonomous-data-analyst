# Power BI Dashboard Design

Use the star schema and DAX measures documented in this folder. Add a consistent date slicer (`dim_date[full_date]`) and optional region/category slicers across business pages.

## Page 1 — Executive Sales Overview

- KPI cards: `[Revenue]`, `[Profit]`, `[Profit Margin]`, `[Total Orders]`, `[Total Customers]`.
- Line chart: `[Revenue]` by `dim_date[full_date]`.
- Bar chart: `[Revenue]` by `dim_region[region]`.
- Bar/column chart: `[Profit]` by `dim_product[category]`.
- Clustered columns: `[Revenue]` and `[Sales Target]` by month.
- Top-products table or bar chart: `dim_product[product_name]`, `[Revenue]`, `[Profit]`; visual-level Top N = 10 by `[Revenue]`.

## Page 2 — Regional Performance

- Matrix: `dim_region[region]`, then `dim_region[state]`, with `[Revenue]`, `[Profit]`, `[Profit Margin]`, and `[Total Orders]`.
- Bar chart: `[Revenue]` by region.
- Bar chart: `[Profit]` by region.
- Bar chart: `[Profit Margin]` by region.
- Line chart: `[Revenue]` by `dim_date[full_date]`, legend `dim_region[region]`.
- State performance table: state, revenue, profit, target achievement.

## Page 3 — Product Performance

- Matrix: category → product name with `[Revenue]`, `[Profit]`, `[Total Quantity]`, `[Discount %]`, and `[Profit Margin]`.
- Column chart: `[Revenue]` by product.
- Column chart: `[Profit]` by product.
- Bar chart: `[Total Quantity]` by product.
- Category chart: `[Revenue]` and `[Profit]` by category.
- Scatter chart: `[Discount %]` versus `[Profit Margin]`, details `dim_product[product_name]`, size `[Revenue]`.
- Top/bottom product tables using Top N/Bottom N visual filters on `[Revenue]` or `[Profit]`.

## Page 4 — Customer Analysis

- KPI cards: `[Total Customers]`, `[Revenue]`, `[Average Order Value]`, `[Customer Order Frequency]`.
- Top-customer table: `dim_customer[customer_id]`, `[Revenue]`, `[Total Orders]`, `[Average Order Value]`.
- Bar chart: top 10 customers by `[Revenue]`.
- Scatter chart: `[Total Orders]` versus `[Revenue]`, details `dim_customer[customer_id]`.

Customer segmentation should remain limited to behavioral measures (revenue, orders, average order value). The current customer dimension has no demographic, channel, or cohort attributes.

## Page 5 — AI Insights

Reserve this page for the existing AI Data Analyst output. It is a report design placeholder only: no existing Power BI-to-Streamlit integration is implemented. Display a short instruction or link to the Streamlit AI Analyst, and keep the page separate from governed SQL measures until an integration is deliberately designed.

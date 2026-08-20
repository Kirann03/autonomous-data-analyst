-- SQLite/PostgreSQL-compatible analytical queries for a future Power BI dataset.

-- 1-6. Headline KPIs: revenue, profit, orders, quantity, average order value, and margin.
SELECT SUM(revenue) AS total_revenue, SUM(profit) AS total_profit,
       COUNT(*) AS total_orders, SUM(quantity) AS total_quantity,
       AVG(revenue) AS average_order_value,
       CASE WHEN SUM(revenue) = 0 THEN NULL ELSE SUM(profit) / SUM(revenue) * 100 END AS profit_margin
FROM fact_sales;

-- 7. Revenue by month.
SELECT d.year, d.month_number, d.month_name, SUM(f.revenue) AS revenue
FROM fact_sales f JOIN dim_date d ON f.date_key = d.date_key
GROUP BY d.year, d.month_number, d.month_name ORDER BY d.year, d.month_number;

-- 8-9. Revenue and profit by region.
SELECT r.region, SUM(f.revenue) AS revenue, SUM(f.profit) AS profit
FROM fact_sales f JOIN dim_region r ON f.region_key = r.region_key
GROUP BY r.region ORDER BY revenue DESC;

-- 10-11. Revenue and profit by category.
SELECT p.category, SUM(f.revenue) AS revenue, SUM(f.profit) AS profit
FROM fact_sales f JOIN dim_product p ON f.product_id = p.product_id
GROUP BY p.category ORDER BY revenue DESC;

-- 12. Top 10 products by revenue.
SELECT p.product_name, SUM(f.revenue) AS revenue
FROM fact_sales f JOIN dim_product p ON f.product_id = p.product_id
GROUP BY p.product_name ORDER BY revenue DESC LIMIT 10;

-- 13. Bottom 10 products by profit.
SELECT p.product_name, SUM(f.profit) AS profit
FROM fact_sales f JOIN dim_product p ON f.product_id = p.product_id
GROUP BY p.product_name ORDER BY profit ASC LIMIT 10;

-- 14. Low-margin products (below 10%).
SELECT p.product_name, SUM(f.revenue) AS revenue, SUM(f.profit) AS profit,
       SUM(f.profit) / NULLIF(SUM(f.revenue), 0) * 100 AS profit_margin
FROM fact_sales f JOIN dim_product p ON f.product_id = p.product_id
GROUP BY p.product_name HAVING SUM(f.profit) / NULLIF(SUM(f.revenue), 0) * 100 < 10
ORDER BY profit_margin;

-- 15. Monthly revenue growth.
WITH monthly_revenue AS (
    SELECT d.year, d.month_number, SUM(f.revenue) AS revenue
    FROM fact_sales f JOIN dim_date d ON f.date_key = d.date_key
    GROUP BY d.year, d.month_number
)
SELECT year, month_number, revenue,
       (revenue - LAG(revenue) OVER (ORDER BY year, month_number))
       / NULLIF(LAG(revenue) OVER (ORDER BY year, month_number), 0) * 100 AS revenue_growth_percent
FROM monthly_revenue ORDER BY year, month_number;

-- 16. Sales target achievement.
SELECT SUM(revenue) AS actual_revenue, SUM(sales_target) AS target_revenue,
       SUM(revenue) / NULLIF(SUM(sales_target), 0) * 100 AS target_achievement_percent
FROM fact_sales;

-- 17. Regions below target.
SELECT r.region, SUM(f.revenue) AS actual_revenue, SUM(f.sales_target) AS target_revenue
FROM fact_sales f JOIN dim_region r ON f.region_key = r.region_key
GROUP BY r.region HAVING SUM(f.revenue) < SUM(f.sales_target)
ORDER BY actual_revenue;

-- 18. Products with margins at least 10 percentage points below the product average.
WITH product_margins AS (
    SELECT p.product_name, SUM(f.profit) / NULLIF(SUM(f.revenue), 0) * 100 AS profit_margin
    FROM fact_sales f JOIN dim_product p ON f.product_id = p.product_id
    GROUP BY p.product_name
), margin_baseline AS (
    SELECT AVG(profit_margin) AS average_margin
    FROM product_margins
)
SELECT product_name, profit_margin
FROM product_margins CROSS JOIN margin_baseline
WHERE profit_margin < average_margin - 10
ORDER BY profit_margin;

-- ============================================================================
-- Phase 7 - Advanced SQL: Window Functions
-- ============================================================================
-- Tested against the SQLite warehouse (see README Phase 7 for the MySQL
-- caveat). Every query below runs against the star schema built in Phase 6:
-- FactSales / FactShipping / FactReturns + DimDate / DimCustomer / DimProduct
-- / DimWarehouse / DimCountry.
-- ============================================================================


-- 1. ROW_NUMBER — order sequence per customer (1st order, 2nd order, ...),
--    the building block for "time between 1st and 2nd purchase" analyses.
SELECT
    fs.order_id,
    fs.customer_key,
    d.full_date AS order_date,
    ROW_NUMBER() OVER (PARTITION BY fs.customer_key ORDER BY d.full_date, fs.order_id) AS order_sequence
FROM (SELECT DISTINCT order_id, customer_key, date_key FROM FactSales) fs
JOIN DimDate d ON fs.date_key = d.date_key
ORDER BY fs.customer_key, order_sequence
LIMIT 100;


-- 2. RANK vs DENSE_RANK — products ranked by revenue within their category.
--    RANK leaves gaps after ties, DENSE_RANK doesn't; both are useful
--    depending on whether "joint 2nd place, then 4th" or "joint 2nd, then 3rd"
--    is the answer you want.
SELECT
    p.category,
    p.product_name,
    ROUND(SUM(fs.line_net_revenue_usd), 2) AS revenue_usd,
    RANK()       OVER (PARTITION BY p.category ORDER BY SUM(fs.line_net_revenue_usd) DESC) AS revenue_rank,
    DENSE_RANK() OVER (PARTITION BY p.category ORDER BY SUM(fs.line_net_revenue_usd) DESC) AS revenue_dense_rank
FROM FactSales fs
JOIN DimProduct p ON fs.product_key = p.product_key
GROUP BY p.category, p.product_name
ORDER BY p.category, revenue_rank
LIMIT 100;


-- 3. Top-3 products per category by gross profit (RANK + filter in an outer
--    query, since window functions can't be filtered directly in WHERE).
SELECT * FROM (
    SELECT
        p.category,
        p.product_name,
        ROUND(SUM(fs.line_gross_profit_usd), 2) AS gross_profit_usd,
        RANK() OVER (PARTITION BY p.category ORDER BY SUM(fs.line_gross_profit_usd) DESC) AS profit_rank
    FROM FactSales fs
    JOIN DimProduct p ON fs.product_key = p.product_key
    GROUP BY p.category, p.product_name
) ranked
WHERE profit_rank <= 3
ORDER BY category, profit_rank;


-- 4. LAG — days between consecutive orders for each customer (a churn /
--    purchase-cadence signal: a widening gap suggests a customer drifting away).
--    Uses julianday() for a correct day-count on real dates (SQLite syntax;
--    MySQL equivalent: DATEDIFF(order_date, LAG(order_date) OVER (...))).
SELECT
    customer_key,
    order_date,
    order_sequence,
    CAST(julianday(order_date) - julianday(LAG(order_date) OVER (
        PARTITION BY customer_key ORDER BY order_date
    )) AS INTEGER) AS days_since_previous_order
FROM (
    SELECT customer_key, order_date,
           ROW_NUMBER() OVER (PARTITION BY customer_key ORDER BY order_date) AS order_sequence
    FROM (SELECT DISTINCT fs.customer_key, d.full_date AS order_date
          FROM FactSales fs JOIN DimDate d ON fs.date_key = d.date_key)
) t
ORDER BY customer_key, order_sequence
LIMIT 200;


-- 5. LEAD — days until a customer's NEXT order (the mirror image of #4;
--    useful for "will this customer buy again within 30/60/90 days").
SELECT
    customer_key,
    order_date,
    CAST(julianday(LEAD(order_date) OVER (
        PARTITION BY customer_key ORDER BY order_date
    )) - julianday(order_date) AS INTEGER) AS days_until_next_order
FROM (SELECT DISTINCT fs.customer_key, d.full_date AS order_date
      FROM FactSales fs JOIN DimDate d ON fs.date_key = d.date_key) t
ORDER BY customer_key, order_date
LIMIT 200;


-- 6. Running total of daily net revenue (cumulative revenue-to-date curve).
SELECT
    d.full_date,
    ROUND(SUM(fs.line_net_revenue_usd), 2) AS daily_revenue_usd,
    ROUND(SUM(SUM(fs.line_net_revenue_usd)) OVER (ORDER BY d.full_date), 2) AS running_total_revenue_usd
FROM FactSales fs JOIN DimDate d ON fs.date_key = d.date_key
GROUP BY d.full_date
ORDER BY d.full_date;


-- 7. 7-day moving average of daily shipping delay — smooths day-to-day noise
--    so a genuine trend (e.g. a partner's service degrading) is visible.
SELECT
    d.full_date,
    ROUND(AVG(fsh.delivery_delay_days), 2) AS avg_delay_that_day,
    ROUND(AVG(AVG(fsh.delivery_delay_days)) OVER (
        ORDER BY d.full_date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    ), 2) AS delay_7day_moving_avg
FROM FactShipping fsh JOIN DimDate d ON fsh.date_key = d.date_key
GROUP BY d.full_date
ORDER BY d.full_date;


-- 8. NTILE(4) — split customers into revenue quartiles (Q1 = top spenders),
--    a quick way to build a value-tiering table without arbitrary cutoffs.
SELECT
    customer_key,
    total_revenue_usd,
    NTILE(4) OVER (ORDER BY total_revenue_usd DESC) AS revenue_quartile
FROM (
    SELECT customer_key, SUM(line_net_revenue_usd) AS total_revenue_usd
    FROM FactSales GROUP BY customer_key
) t
ORDER BY total_revenue_usd DESC
LIMIT 200;


-- 9. FIRST_VALUE / LAST_VALUE — each customer's first and most recent order
--    date, alongside every order row (no separate self-join needed).
SELECT DISTINCT
    fs.customer_key,
    d.full_date AS order_date,
    FIRST_VALUE(d.full_date) OVER (PARTITION BY fs.customer_key ORDER BY d.full_date) AS first_order_date,
    LAST_VALUE(d.full_date) OVER (
        PARTITION BY fs.customer_key ORDER BY d.full_date
        ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
    ) AS most_recent_order_date
FROM FactSales fs JOIN DimDate d ON fs.date_key = d.date_key
ORDER BY fs.customer_key
LIMIT 200;


-- 10. PERCENT_RANK — where does each warehouse's average outbound shipping
--     delay sit relative to all other warehouses (0 = fastest, 1 = slowest)?
--     Useful for flagging "worst decile" warehouses for a logistics review.
SELECT
    w.warehouse_id,
    w.warehouse_name,
    ROUND(AVG(fsh.delivery_delay_days), 2) AS avg_delay_days,
    ROUND(PERCENT_RANK() OVER (ORDER BY AVG(fsh.delivery_delay_days)), 4) AS delay_percentile
FROM FactShipping fsh
JOIN DimWarehouse w ON fsh.origin_warehouse_key = w.warehouse_key
GROUP BY w.warehouse_id, w.warehouse_name
ORDER BY delay_percentile DESC
LIMIT 20;


-- 11. Cumulative distribution of order value (CUME_DIST) — "what fraction of
--     orders are at or below this order's value" - useful for setting a
--     "high-value order" alert threshold (e.g. the 95th percentile).
SELECT
    order_id,
    order_value_usd,
    ROUND(CUME_DIST() OVER (ORDER BY order_value_usd), 4) AS cume_dist
FROM (
    SELECT order_id, SUM(line_net_revenue_usd) AS order_value_usd
    FROM FactSales GROUP BY order_id
) t
ORDER BY order_value_usd DESC
LIMIT 50;


-- 12. Rank shipping partners by average delay, per destination country
--     (identifies whether a partner is uniformly bad, or only bad on
--     specific lanes).
SELECT
    dc.country_name,
    fsh.partner_id,
    ROUND(AVG(fsh.delivery_delay_days), 2) AS avg_delay_days,
    RANK() OVER (PARTITION BY dc.country_name ORDER BY AVG(fsh.delivery_delay_days) DESC) AS worst_partner_rank
FROM FactShipping fsh
JOIN DimCountry dc ON fsh.destination_country_key = dc.country_key
GROUP BY dc.country_name, fsh.partner_id
ORDER BY dc.country_name, worst_partner_rank
LIMIT 100;


-- 13. Month-over-month revenue change per country using LAG (growth/decline
--     signal feeding the "which countries are shrinking" business question).
SELECT
    country_name,
    year, month,
    monthly_revenue_usd,
    ROUND(monthly_revenue_usd - LAG(monthly_revenue_usd) OVER (
        PARTITION BY country_name ORDER BY year, month
    ), 2) AS mom_change_usd
FROM (
    SELECT dc.country_name, d.year, d.month, SUM(fs.line_net_revenue_usd) AS monthly_revenue_usd
    FROM FactSales fs
    JOIN DimDate d ON fs.date_key = d.date_key
    JOIN DimCountry dc ON fs.country_key = dc.country_key
    GROUP BY dc.country_name, d.year, d.month
) t
ORDER BY country_name, year, month;

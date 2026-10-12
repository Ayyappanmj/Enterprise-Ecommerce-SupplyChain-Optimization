-- ============================================================================
-- Phase 7 - Advanced SQL: Views
-- ============================================================================
-- Reusable views over the star schema, so Power BI (Phase 8) and ad-hoc
-- analysis can query a clean, named view instead of repeating the same
-- 4-table join everywhere. All tested against the SQLite warehouse.
-- ============================================================================

DROP VIEW IF EXISTS vw_order_line_profitability;
DROP VIEW IF EXISTS vw_country_performance;
DROP VIEW IF EXISTS vw_customer_summary;
DROP VIEW IF EXISTS vw_product_performance;
DROP VIEW IF EXISTS vw_warehouse_shipping_performance;
DROP VIEW IF EXISTS vw_monthly_sales_trend;
DROP VIEW IF EXISTS vw_return_hotspots;
DROP VIEW IF EXISTS vw_repeat_customers;
DROP VIEW IF EXISTS vw_shipping_delay_by_route;
DROP VIEW IF EXISTS vw_daily_kpi;


-- 1. Every sales line item with its full dimension context and per-line
--    margin already computed - the base view most other analysis builds on.
CREATE VIEW vw_order_line_profitability AS
SELECT
    fs.order_id, fs.order_item_id, d.full_date AS order_date, d.year, d.quarter, d.month,
    c.customer_id, c.segment AS customer_segment, c.loyalty_tier,
    p.product_id, p.product_name, p.category, p.sub_category,
    w.warehouse_id, w.warehouse_name,
    co.country_name, co.region_name,
    fs.quantity, fs.unit_price_usd, fs.unit_cost_usd,
    fs.line_net_revenue_usd, fs.line_cost_usd, fs.line_gross_profit_usd,
    ROUND(fs.line_gross_profit_usd / NULLIF(fs.line_net_revenue_usd, 0), 4) AS gross_margin_pct
FROM FactSales fs
JOIN DimDate d ON fs.date_key = d.date_key
JOIN DimCustomer c ON fs.customer_key = c.customer_key
JOIN DimProduct p ON fs.product_key = p.product_key
JOIN DimWarehouse w ON fs.warehouse_key = w.warehouse_key
JOIN DimCountry co ON fs.country_key = co.country_key;


-- 2. Country-level rollup: revenue, margin, order count, return count.
CREATE VIEW vw_country_performance AS
SELECT
    co.country_name, co.region_name,
    COUNT(DISTINCT fs.order_id) AS num_orders,
    ROUND(SUM(fs.line_net_revenue_usd), 2) AS revenue_usd,
    ROUND(SUM(fs.line_gross_profit_usd), 2) AS gross_profit_usd,
    ROUND(SUM(fs.line_gross_profit_usd) / NULLIF(SUM(fs.line_net_revenue_usd), 0), 4) AS gross_margin_pct,
    (SELECT COUNT(*) FROM FactReturns fr
        JOIN FactSales fs2 ON fr.order_id = fs2.order_id AND fs2.country_key = co.country_key) AS num_returns
FROM FactSales fs
JOIN DimCountry co ON fs.country_key = co.country_key
GROUP BY co.country_name, co.region_name;


-- 3. Per-customer summary: revenue, order count, first/last order, tier.
CREATE VIEW vw_customer_summary AS
SELECT
    c.customer_id, c.segment, c.loyalty_tier, co.country_name,
    COUNT(DISTINCT fs.order_id) AS num_orders,
    ROUND(SUM(fs.line_net_revenue_usd), 2) AS total_revenue_usd,
    ROUND(SUM(fs.line_net_revenue_usd) / NULLIF(COUNT(DISTINCT fs.order_id), 0), 2) AS avg_order_value_usd,
    MIN(d.full_date) AS first_order_date,
    MAX(d.full_date) AS last_order_date
FROM FactSales fs
JOIN DimCustomer c ON fs.customer_key = c.customer_key
JOIN DimCountry co ON c.country_key = co.country_key
JOIN DimDate d ON fs.date_key = d.date_key
GROUP BY c.customer_id, c.segment, c.loyalty_tier, co.country_name;


-- 4. Per-product performance: units sold, revenue, margin, return rate.
CREATE VIEW vw_product_performance AS
SELECT
    p.product_id, p.product_name, p.category, p.sub_category,
    SUM(fs.quantity) AS units_sold,
    ROUND(SUM(fs.line_net_revenue_usd), 2) AS revenue_usd,
    ROUND(SUM(fs.line_gross_profit_usd), 2) AS gross_profit_usd,
    ROUND(SUM(fs.line_gross_profit_usd) / NULLIF(SUM(fs.line_net_revenue_usd), 0), 4) AS gross_margin_pct,
    (SELECT COUNT(*) FROM FactReturns fr WHERE fr.product_key = p.product_key) AS num_returns,
    ROUND((SELECT COUNT(*) FROM FactReturns fr WHERE fr.product_key = p.product_key) * 1.0
          / NULLIF(COUNT(fs.order_item_id), 0), 4) AS return_rate
FROM FactSales fs
JOIN DimProduct p ON fs.product_key = p.product_key
GROUP BY p.product_id, p.product_name, p.category, p.sub_category;


-- 5. Warehouse shipping performance: volume, avg delay, % delayed shipments.
CREATE VIEW vw_warehouse_shipping_performance AS
SELECT
    w.warehouse_id, w.warehouse_name, w.warehouse_type, co.country_name,
    COUNT(*) AS shipments,
    ROUND(AVG(fsh.delivery_delay_days), 2) AS avg_delay_days,
    ROUND(AVG(CASE WHEN fsh.is_delayed THEN 1.0 ELSE 0 END), 4) AS pct_delayed
FROM FactShipping fsh
JOIN DimWarehouse w ON fsh.origin_warehouse_key = w.warehouse_key
JOIN DimCountry co ON w.country_key = co.country_key
GROUP BY w.warehouse_id, w.warehouse_name, w.warehouse_type, co.country_name;


-- 6. Monthly sales trend: revenue, orders, margin by calendar month.
CREATE VIEW vw_monthly_sales_trend AS
SELECT
    d.year, d.month, d.month_name,
    COUNT(DISTINCT fs.order_id) AS num_orders,
    ROUND(SUM(fs.line_net_revenue_usd), 2) AS revenue_usd,
    ROUND(SUM(fs.line_gross_profit_usd), 2) AS gross_profit_usd,
    ROUND(SUM(fs.line_gross_profit_usd) / NULLIF(SUM(fs.line_net_revenue_usd), 0), 4) AS gross_margin_pct
FROM FactSales fs
JOIN DimDate d ON fs.date_key = d.date_key
GROUP BY d.year, d.month, d.month_name;


-- 7. Return hotspots: which product x reason combinations drive the most
--    refund dollars (the single most actionable view for margin recovery).
CREATE VIEW vw_return_hotspots AS
SELECT
    p.category, p.product_name, fr.return_reason,
    COUNT(*) AS num_returns,
    ROUND(SUM(fr.refund_amount_usd), 2) AS total_refund_usd,
    ROUND(AVG(fr.refund_amount_usd), 2) AS avg_refund_usd
FROM FactReturns fr
JOIN DimProduct p ON fr.product_key = p.product_key
GROUP BY p.category, p.product_name, fr.return_reason;


-- 8. Repeat customers only, with order count and revenue - the input to
--    most retention / loyalty analysis.
CREATE VIEW vw_repeat_customers AS
SELECT customer_id, segment, loyalty_tier, country_name, num_orders,
       total_revenue_usd, avg_order_value_usd, first_order_date, last_order_date
FROM vw_customer_summary
WHERE num_orders > 1;


-- 9. Shipping delay by route (origin warehouse -> destination country),
--    the grain "shipping bottlenecks" analysis needs.
CREATE VIEW vw_shipping_delay_by_route AS
SELECT
    w.warehouse_id AS origin_warehouse_id, w.warehouse_name AS origin_warehouse,
    co.country_name AS destination_country,
    fsh.route_id, fsh.partner_id,
    COUNT(*) AS shipments,
    ROUND(AVG(fsh.delivery_delay_days), 2) AS avg_delay_days,
    ROUND(AVG(CASE WHEN fsh.is_delayed THEN 1.0 ELSE 0 END), 4) AS pct_delayed
FROM FactShipping fsh
JOIN DimWarehouse w ON fsh.origin_warehouse_key = w.warehouse_key
JOIN DimCountry co ON fsh.destination_country_key = co.country_key
GROUP BY w.warehouse_id, w.warehouse_name, co.country_name, fsh.route_id, fsh.partner_id;


-- 10. Single-row-per-day KPI view: revenue, orders, avg delay, returns -
--     built for a "daily ops" dashboard tile.
CREATE VIEW vw_daily_kpi AS
SELECT
    d.full_date,
    COUNT(DISTINCT fs.order_id) AS num_orders,
    ROUND(SUM(fs.line_net_revenue_usd), 2) AS revenue_usd,
    ROUND(SUM(fs.line_gross_profit_usd), 2) AS gross_profit_usd,
    (SELECT ROUND(AVG(delivery_delay_days), 2) FROM FactShipping s
        JOIN DimDate d2 ON s.date_key = d2.date_key WHERE d2.full_date = d.full_date) AS avg_delay_that_day,
    (SELECT COUNT(*) FROM FactReturns r
        JOIN DimDate d3 ON r.date_key = d3.date_key WHERE d3.full_date = d.full_date) AS num_returns_that_day
FROM FactSales fs
JOIN DimDate d ON fs.date_key = d.date_key
GROUP BY d.full_date;

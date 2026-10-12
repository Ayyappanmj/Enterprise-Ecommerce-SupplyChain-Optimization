-- ============================================================================
-- Phase 7 - Advanced SQL: Business Queries (100+)
-- ============================================================================
-- Every query in this file was executed against the SQLite warehouse built
-- in Phase 6. Dialect notes for MySQL are in README Phase 7 (date functions
-- such as strftime/julianday/date() and printf() need MySQL equivalents).
-- Organized by business area; each query is numbered and one-line-commented
-- with the question it answers.
-- ============================================================================


-- ============================================================
-- A. REVENUE & SALES PERFORMANCE
-- ============================================================

-- A1. Overall revenue, orders, and average order value.
SELECT
    COUNT(DISTINCT order_id) AS total_orders,
    ROUND(SUM(line_net_revenue_usd), 2) AS total_revenue_usd,
    ROUND(SUM(line_net_revenue_usd) / COUNT(DISTINCT order_id), 2) AS avg_order_value_usd
FROM FactSales;

-- A2. Revenue and order count by product category.
SELECT p.category, COUNT(DISTINCT fs.order_id) AS orders,
       ROUND(SUM(fs.line_net_revenue_usd), 2) AS revenue_usd
FROM FactSales fs JOIN DimProduct p ON fs.product_key = p.product_key
GROUP BY p.category ORDER BY revenue_usd DESC;

-- A3. Revenue by region.
SELECT co.region_name, ROUND(SUM(fs.line_net_revenue_usd), 2) AS revenue_usd
FROM FactSales fs JOIN DimCountry co ON fs.country_key = co.country_key
GROUP BY co.region_name ORDER BY revenue_usd DESC;

-- A4. Revenue by year and quarter.
SELECT d.year, d.quarter, ROUND(SUM(fs.line_net_revenue_usd), 2) AS revenue_usd
FROM FactSales fs JOIN DimDate d ON fs.date_key = d.date_key
GROUP BY d.year, d.quarter ORDER BY d.year, d.quarter;

-- A5. Top 10 products by revenue.
SELECT p.product_name, p.category, ROUND(SUM(fs.line_net_revenue_usd), 2) AS revenue_usd
FROM FactSales fs JOIN DimProduct p ON fs.product_key = p.product_key
GROUP BY p.product_name, p.category ORDER BY revenue_usd DESC LIMIT 10;

-- A6. Top 10 customers by lifetime revenue.
SELECT c.customer_id, ROUND(SUM(fs.line_net_revenue_usd), 2) AS lifetime_revenue_usd
FROM FactSales fs JOIN DimCustomer c ON fs.customer_key = c.customer_key
GROUP BY c.customer_id ORDER BY lifetime_revenue_usd DESC LIMIT 10;

-- A7. Revenue by customer segment (Consumer / SMB / Corporate).
SELECT c.segment, COUNT(DISTINCT fs.order_id) AS orders,
       ROUND(SUM(fs.line_net_revenue_usd), 2) AS revenue_usd
FROM FactSales fs JOIN DimCustomer c ON fs.customer_key = c.customer_key
GROUP BY c.segment ORDER BY revenue_usd DESC;

-- A8. Revenue by loyalty tier.
SELECT c.loyalty_tier, ROUND(SUM(fs.line_net_revenue_usd), 2) AS revenue_usd,
       ROUND(AVG(fs.line_net_revenue_usd), 2) AS avg_line_value_usd
FROM FactSales fs JOIN DimCustomer c ON fs.customer_key = c.customer_key
GROUP BY c.loyalty_tier ORDER BY revenue_usd DESC;

-- A9. Order count and revenue by day of week (are weekends slower?).
SELECT d.day_name, COUNT(DISTINCT fs.order_id) AS orders,
       ROUND(SUM(fs.line_net_revenue_usd), 2) AS revenue_usd
FROM FactSales fs JOIN DimDate d ON fs.date_key = d.date_key
GROUP BY d.day_name, d.day_of_week ORDER BY d.day_of_week;

-- A10. Revenue by fulfilling warehouse (which warehouses drive the most sales).
SELECT w.warehouse_id, w.warehouse_name, ROUND(SUM(fs.line_net_revenue_usd), 2) AS revenue_usd
FROM FactSales fs JOIN DimWarehouse w ON fs.warehouse_key = w.warehouse_key
GROUP BY w.warehouse_id, w.warehouse_name ORDER BY revenue_usd DESC LIMIT 10;


-- ============================================================
-- B. GROSS MARGIN / PROFITABILITY
-- ============================================================

-- B1. Overall gross profit and gross margin %.
SELECT ROUND(SUM(line_net_revenue_usd), 2) AS revenue_usd,
       ROUND(SUM(line_gross_profit_usd), 2) AS gross_profit_usd,
       ROUND(SUM(line_gross_profit_usd) / SUM(line_net_revenue_usd), 4) AS gross_margin_pct
FROM FactSales;

-- B2. Gross margin % by category.
SELECT p.category,
       ROUND(SUM(fs.line_gross_profit_usd) / SUM(fs.line_net_revenue_usd), 4) AS gross_margin_pct
FROM FactSales fs JOIN DimProduct p ON fs.product_key = p.product_key
GROUP BY p.category ORDER BY gross_margin_pct DESC;

-- B3. Highest-margin products (min 50 units sold, to exclude small-sample noise).
SELECT p.product_name, p.category, SUM(fs.quantity) AS units_sold,
       ROUND(SUM(fs.line_gross_profit_usd) / SUM(fs.line_net_revenue_usd), 4) AS gross_margin_pct
FROM FactSales fs JOIN DimProduct p ON fs.product_key = p.product_key
GROUP BY p.product_name, p.category
HAVING SUM(fs.quantity) >= 50
ORDER BY gross_margin_pct DESC LIMIT 15;

-- B4. Lowest-margin products (candidates for re-pricing or supplier renegotiation).
SELECT p.product_name, p.category, SUM(fs.quantity) AS units_sold,
       ROUND(SUM(fs.line_gross_profit_usd) / SUM(fs.line_net_revenue_usd), 4) AS gross_margin_pct
FROM FactSales fs JOIN DimProduct p ON fs.product_key = p.product_key
GROUP BY p.product_name, p.category
HAVING SUM(fs.quantity) >= 50
ORDER BY gross_margin_pct ASC LIMIT 15;

-- B5. Gross margin % by fulfilling warehouse (lowest first).
SELECT w.warehouse_id, w.warehouse_name,
       ROUND(SUM(fs.line_gross_profit_usd) / SUM(fs.line_net_revenue_usd), 4) AS gross_margin_pct
FROM FactSales fs JOIN DimWarehouse w ON fs.warehouse_key = w.warehouse_key
GROUP BY w.warehouse_id, w.warehouse_name ORDER BY gross_margin_pct ASC LIMIT 15;

-- B6. Gross margin % by customer segment.
SELECT c.segment,
       ROUND(SUM(fs.line_gross_profit_usd) / SUM(fs.line_net_revenue_usd), 4) AS gross_margin_pct
FROM FactSales fs JOIN DimCustomer c ON fs.customer_key = c.customer_key
GROUP BY c.segment ORDER BY gross_margin_pct DESC;

-- B7. Monthly gross margin trend (is margin compressing or improving over
--     time? - the project's central question).
SELECT d.year, d.month,
       ROUND(SUM(fs.line_net_revenue_usd), 2) AS revenue_usd,
       ROUND(SUM(fs.line_gross_profit_usd), 2) AS gross_profit_usd,
       ROUND(SUM(fs.line_gross_profit_usd) / SUM(fs.line_net_revenue_usd), 4) AS gross_margin_pct
FROM FactSales fs JOIN DimDate d ON fs.date_key = d.date_key
GROUP BY d.year, d.month ORDER BY d.year, d.month;

-- B8. Margin impact of discounting: gross margin % by discount band.
SELECT
    CASE WHEN order_discount_pct = 0 THEN 'No discount'
         WHEN order_discount_pct <= 0.10 THEN '1-10%'
         WHEN order_discount_pct <= 0.20 THEN '11-20%'
         ELSE '21%+' END AS discount_band,
    COUNT(DISTINCT order_id) AS orders,
    ROUND(SUM(line_gross_profit_usd) / SUM(line_net_revenue_usd), 4) AS gross_margin_pct
FROM FactSales
GROUP BY discount_band ORDER BY gross_margin_pct DESC;

-- B9. Products where returns erode the most profit (gross profit vs refunds
--     paid out for that product).
SELECT p.product_name, p.category,
       ROUND(SUM(fs.line_gross_profit_usd), 2) AS gross_profit_usd,
       ROUND(COALESCE(r.total_refunded, 0), 2) AS total_refunded_usd,
       ROUND(SUM(fs.line_gross_profit_usd) - COALESCE(r.total_refunded, 0), 2) AS profit_after_returns_usd
FROM FactSales fs
JOIN DimProduct p ON fs.product_key = p.product_key
LEFT JOIN (SELECT product_key, SUM(refund_amount_usd) AS total_refunded FROM FactReturns GROUP BY product_key) r
    ON fs.product_key = r.product_key
GROUP BY p.product_name, p.category, r.total_refunded
ORDER BY profit_after_returns_usd ASC LIMIT 15;

-- B10. Profit after returns by country: gross profit minus refunds paid on
--      that country's orders. (Refunds are pre-aggregated per order to avoid
--      multiplying sales rows in the join.)
SELECT co.country_name,
       ROUND(SUM(fs.line_gross_profit_usd), 2) AS gross_profit_usd,
       ROUND(COALESCE((SELECT SUM(fr.refund_amount_usd) FROM FactReturns fr
                       WHERE fr.order_id IN (SELECT DISTINCT order_id FROM FactSales x WHERE x.country_key = co.country_key)), 0), 2) AS refunds_usd
FROM FactSales fs JOIN DimCountry co ON fs.country_key = co.country_key
GROUP BY co.country_name, co.country_key
ORDER BY gross_profit_usd DESC;

-- B11. Margin quartiles across all products (NTILE) - how much of the
--      catalog's revenue sits in each margin quartile?
SELECT margin_quartile, COUNT(*) AS num_products, ROUND(SUM(revenue_usd), 2) AS revenue_usd
FROM (
    SELECT p.product_id, SUM(fs.line_net_revenue_usd) AS revenue_usd,
           NTILE(4) OVER (ORDER BY SUM(fs.line_gross_profit_usd) / SUM(fs.line_net_revenue_usd) DESC) AS margin_quartile
    FROM FactSales fs JOIN DimProduct p ON fs.product_key = p.product_key
    GROUP BY p.product_id
) t
GROUP BY margin_quartile ORDER BY margin_quartile;

-- B12. Supplier-level margin (supplier_id is a degenerate attribute on
--      DimProduct - there is no DimSupplier in this star schema by design).
SELECT p.supplier_id,
       ROUND(SUM(fs.line_net_revenue_usd), 2) AS revenue_usd,
       ROUND(SUM(fs.line_gross_profit_usd) / SUM(fs.line_net_revenue_usd), 4) AS gross_margin_pct
FROM FactSales fs JOIN DimProduct p ON fs.product_key = p.product_key
GROUP BY p.supplier_id ORDER BY gross_margin_pct ASC LIMIT 15;


-- ============================================================
-- C. CUSTOMER ANALYTICS: CLV, AOV, REPEAT PURCHASE, RETENTION
-- ============================================================

-- C1. Customer Lifetime Value distribution (min / avg / max).
SELECT MIN(total_revenue_usd) AS min_clv, ROUND(AVG(total_revenue_usd), 2) AS avg_clv,
       MAX(total_revenue_usd) AS max_clv
FROM (SELECT customer_key, SUM(line_net_revenue_usd) AS total_revenue_usd FROM FactSales GROUP BY customer_key);

-- C2. Top 20 customers by CLV, with order count and AOV.
SELECT c.customer_id, c.segment, c.loyalty_tier,
       COUNT(DISTINCT fs.order_id) AS num_orders,
       ROUND(SUM(fs.line_net_revenue_usd), 2) AS clv_usd,
       ROUND(SUM(fs.line_net_revenue_usd) / COUNT(DISTINCT fs.order_id), 2) AS avg_order_value_usd
FROM FactSales fs JOIN DimCustomer c ON fs.customer_key = c.customer_key
GROUP BY c.customer_id, c.segment, c.loyalty_tier
ORDER BY clv_usd DESC LIMIT 20;

-- C3. Repeat purchase rate overall (% of customers with 2+ distinct orders).
SELECT ROUND(SUM(CASE WHEN num_orders > 1 THEN 1 ELSE 0 END) * 1.0 / COUNT(*), 4) AS repeat_purchase_rate,
       COUNT(*) AS total_purchasing_customers
FROM (SELECT customer_key, COUNT(DISTINCT order_id) AS num_orders FROM FactSales GROUP BY customer_key);

-- C4. Repeat purchase rate by segment.
SELECT c.segment,
       ROUND(SUM(CASE WHEN t.num_orders > 1 THEN 1 ELSE 0 END) * 1.0 / COUNT(*), 4) AS repeat_purchase_rate
FROM (SELECT customer_key, COUNT(DISTINCT order_id) AS num_orders FROM FactSales GROUP BY customer_key) t
JOIN DimCustomer c ON t.customer_key = c.customer_key
GROUP BY c.segment;

-- C5. Average order value by country.
SELECT co.country_name,
       ROUND(SUM(fs.line_net_revenue_usd) / COUNT(DISTINCT fs.order_id), 2) AS avg_order_value_usd
FROM FactSales fs JOIN DimCountry co ON fs.country_key = co.country_key
GROUP BY co.country_name ORDER BY avg_order_value_usd DESC;

-- C6. Purchasing customers by signup month.
SELECT strftime('%Y-%m', c.signup_date) AS signup_month, COUNT(*) AS purchasing_customers
FROM DimCustomer c
WHERE c.customer_key IN (SELECT DISTINCT customer_key FROM FactSales)
GROUP BY signup_month ORDER BY signup_month;

-- C7. Customers who have never had an order returned (a "low-friction"
--     cohort worth understanding for retention messaging).
SELECT COUNT(DISTINCT customer_key) AS customers_with_no_returned_orders
FROM FactSales
WHERE customer_key NOT IN (
    SELECT DISTINCT fs2.customer_key FROM FactSales fs2 JOIN FactReturns fr ON fr.order_id = fs2.order_id
);

-- C8. Customer value quartiles (NTILE) with headcount and share of revenue.
SELECT clv_quartile, COUNT(*) AS num_customers, ROUND(SUM(clv_usd), 2) AS revenue_usd,
       ROUND(SUM(clv_usd) * 100.0 / SUM(SUM(clv_usd)) OVER (), 2) AS pct_of_total_revenue
FROM (
    SELECT customer_key, SUM(line_net_revenue_usd) AS clv_usd,
           NTILE(4) OVER (ORDER BY SUM(line_net_revenue_usd) DESC) AS clv_quartile
    FROM FactSales GROUP BY customer_key
) t
GROUP BY clv_quartile ORDER BY clv_quartile;

-- C9. Customers active in the most recent 90 days of the dataset.
SELECT COUNT(DISTINCT fs.customer_key) AS active_customers_last_90d
FROM FactSales fs JOIN DimDate d ON fs.date_key = d.date_key
WHERE d.full_date >= (SELECT date(MAX(full_date), '-90 days') FROM DimDate);

-- C10. Cohort table: customers grouped by first-purchase month.
SELECT strftime('%Y-%m', first_purchase) AS first_purchase_month, COUNT(*) AS customers
FROM (SELECT fs.customer_key, MIN(d.full_date) AS first_purchase
      FROM FactSales fs JOIN DimDate d ON fs.date_key = d.date_key GROUP BY fs.customer_key)
GROUP BY first_purchase_month ORDER BY first_purchase_month;

-- C11. Monthly cohort RETENTION curve. A recursive CTE builds a complete
--      0..11 month-offset spine per cohort, so offsets with zero activity
--      still appear as 0% rather than silently disappearing (the classic
--      reason to reach for a recursive CTE over a plain GROUP BY).
WITH RECURSIVE month_offsets(n) AS (
    SELECT 0
    UNION ALL
    SELECT n + 1 FROM month_offsets WHERE n < 11
),
cohorts AS (
    SELECT customer_key, MIN(date_key / 100) AS cohort_month   -- YYYYMM from YYYYMMDD
    FROM FactSales GROUP BY customer_key
),
cohort_activity AS (
    SELECT DISTINCT c.cohort_month, fs.date_key / 100 AS activity_month, fs.customer_key
    FROM FactSales fs JOIN cohorts c ON fs.customer_key = c.customer_key
),
cohort_sizes AS (
    SELECT cohort_month, COUNT(*) AS cohort_size FROM cohorts GROUP BY cohort_month
),
spine AS (
    SELECT cs.cohort_month, mo.n AS month_offset, cs.cohort_size
    FROM cohort_sizes cs CROSS JOIN month_offsets mo
)
SELECT
    s.cohort_month, s.month_offset,
    COUNT(ca.customer_key) AS active_customers,
    s.cohort_size,
    ROUND(COUNT(ca.customer_key) * 1.0 / s.cohort_size, 4) AS retention_rate
FROM spine s
LEFT JOIN cohort_activity ca ON ca.cohort_month = s.cohort_month
    AND (ca.activity_month / 100 - s.cohort_month / 100) * 12
        + (ca.activity_month % 100 - s.cohort_month % 100) = s.month_offset
GROUP BY s.cohort_month, s.month_offset, s.cohort_size
ORDER BY s.cohort_month, s.month_offset
LIMIT 60;

-- C12. Customers with the longest gap between consecutive orders (churn-risk
--      watchlist candidates) using LAG.
SELECT customer_key, order_date, days_since_previous
FROM (
    SELECT customer_key, order_date,
           CAST(julianday(order_date) - julianday(LAG(order_date) OVER (
               PARTITION BY customer_key ORDER BY order_date)) AS INTEGER) AS days_since_previous
    FROM (SELECT DISTINCT fs.customer_key, d.full_date AS order_date
          FROM FactSales fs JOIN DimDate d ON fs.date_key = d.date_key)
) t
WHERE days_since_previous IS NOT NULL
ORDER BY days_since_previous DESC LIMIT 20;

-- C13. Average number of distinct order dates per customer, by segment.
SELECT c.segment, ROUND(AVG(t.num_order_dates), 2) AS avg_order_dates
FROM (SELECT customer_key, COUNT(DISTINCT date_key) AS num_order_dates FROM FactSales GROUP BY customer_key) t
JOIN DimCustomer c ON t.customer_key = c.customer_key
GROUP BY c.segment;

-- C14. Loyalty tier vs. actual spend - do "Platinum" customers really spend
--      the most, or is the tier stale/mislabeled?
SELECT c.loyalty_tier, COUNT(DISTINCT c.customer_key) AS customers,
       ROUND(AVG(t.total_revenue), 2) AS avg_revenue_per_customer
FROM DimCustomer c
JOIN (SELECT customer_key, SUM(line_net_revenue_usd) AS total_revenue FROM FactSales GROUP BY customer_key) t
    ON c.customer_key = t.customer_key
GROUP BY c.loyalty_tier ORDER BY avg_revenue_per_customer DESC;

-- C15. Customers whose most recent order was returned (a "left on a bad
--      note" flag worth a customer-success follow-up).
SELECT DISTINCT c.customer_id
FROM DimCustomer c
JOIN (
    SELECT customer_key, order_id,
           ROW_NUMBER() OVER (PARTITION BY customer_key ORDER BY date_key DESC, order_id DESC) AS rn
    FROM (SELECT DISTINCT customer_key, order_id, date_key FROM FactSales)
) last_order ON c.customer_key = last_order.customer_key AND last_order.rn = 1
JOIN FactReturns fr ON fr.order_id = last_order.order_id
LIMIT 20;


-- ============================================================
-- D. PRODUCT PERFORMANCE & RETURNS
-- ============================================================

-- D1. Return rate by product (returned line items / sold line items).
--     OPTIMIZED: each side is aggregated to one row per product FIRST, then
--     the two small results are joined. The naive version joined 1.5M sales
--     rows to returns and ran COUNT(DISTINCT) over the product - >8s here;
--     this form is a single pass over each table.
SELECT p.product_name, p.category, s.lines_sold,
       COALESCE(r.returns, 0) AS returns,
       ROUND(COALESCE(r.returns, 0) * 1.0 / s.lines_sold, 4) AS return_rate
FROM (SELECT product_key, COUNT(*) AS lines_sold FROM FactSales GROUP BY product_key) s
JOIN DimProduct p ON p.product_key = s.product_key
LEFT JOIN (SELECT product_key, COUNT(*) AS returns FROM FactReturns GROUP BY product_key) r
    ON r.product_key = s.product_key
WHERE s.lines_sold >= 30
ORDER BY return_rate DESC LIMIT 20;

-- D2. Return rate by category.
--     OPTIMIZED the same way as D1 (aggregate per product, then roll up).
SELECT p.category, SUM(s.lines_sold) AS lines_sold, SUM(COALESCE(r.returns, 0)) AS returns,
       ROUND(SUM(COALESCE(r.returns, 0)) * 1.0 / SUM(s.lines_sold), 4) AS return_rate
FROM (SELECT product_key, COUNT(*) AS lines_sold FROM FactSales GROUP BY product_key) s
JOIN DimProduct p ON p.product_key = s.product_key
LEFT JOIN (SELECT product_key, COUNT(*) AS returns FROM FactReturns GROUP BY product_key) r
    ON r.product_key = s.product_key
GROUP BY p.category ORDER BY return_rate DESC;

-- D3. Top return reasons overall.
SELECT return_reason, COUNT(*) AS num_returns, ROUND(SUM(refund_amount_usd), 2) AS total_refund_usd
FROM FactReturns GROUP BY return_reason ORDER BY num_returns DESC;

-- D4. Return hotspots: category x reason combinations with the highest refund $.
SELECT p.category, fr.return_reason, COUNT(*) AS num_returns,
       ROUND(SUM(fr.refund_amount_usd), 2) AS total_refund_usd
FROM FactReturns fr JOIN DimProduct p ON fr.product_key = p.product_key
GROUP BY p.category, fr.return_reason ORDER BY total_refund_usd DESC LIMIT 15;

-- D5. Return condition breakdown (how many returns come back damaged/unopened).
SELECT return_condition, COUNT(*) AS num_returns,
       ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM FactReturns), 2) AS pct_of_returns
FROM FactReturns GROUP BY return_condition ORDER BY num_returns DESC;

-- D6. Products with the highest refund-to-revenue ratio.
SELECT p.product_name,
       ROUND(SUM(fs.line_net_revenue_usd), 2) AS revenue_usd,
       ROUND(COALESCE(r.total_refund, 0), 2) AS refund_usd,
       ROUND(COALESCE(r.total_refund, 0) / SUM(fs.line_net_revenue_usd), 4) AS refund_to_revenue_ratio
FROM FactSales fs
JOIN DimProduct p ON fs.product_key = p.product_key
LEFT JOIN (SELECT product_key, SUM(refund_amount_usd) AS total_refund FROM FactReturns GROUP BY product_key) r
    ON fs.product_key = r.product_key
GROUP BY p.product_name, r.total_refund
HAVING revenue_usd > 100
ORDER BY refund_to_revenue_ratio DESC LIMIT 15;

-- D7. Monthly return volume trend.
SELECT d.year, d.month, COUNT(*) AS num_returns, ROUND(SUM(fr.refund_amount_usd), 2) AS total_refund_usd
FROM FactReturns fr JOIN DimDate d ON fr.date_key = d.date_key
GROUP BY d.year, d.month ORDER BY d.year, d.month;

-- D8. Units sold by sub-category, ranked within category (DENSE_RANK).
SELECT category, sub_category, units_sold,
       DENSE_RANK() OVER (PARTITION BY category ORDER BY units_sold DESC) AS rank_in_category
FROM (
    SELECT p.category, p.sub_category, SUM(fs.quantity) AS units_sold
    FROM FactSales fs JOIN DimProduct p ON fs.product_key = p.product_key
    GROUP BY p.category, p.sub_category
) t
ORDER BY category, rank_in_category;

-- D9. Products never returned at all (20+ units sold) - a positive-signal
--     list for merchandising.
SELECT p.product_name, p.category, SUM(fs.quantity) AS units_sold
FROM FactSales fs JOIN DimProduct p ON fs.product_key = p.product_key
WHERE fs.product_key NOT IN (SELECT DISTINCT product_key FROM FactReturns)
GROUP BY p.product_name, p.category
HAVING units_sold >= 20
ORDER BY units_sold DESC LIMIT 15;

-- D10. Average refund amount by category.
SELECT p.category, ROUND(AVG(fr.refund_amount_usd), 2) AS avg_refund_usd, COUNT(*) AS num_returns
FROM FactReturns fr JOIN DimProduct p ON fr.product_key = p.product_key
GROUP BY p.category ORDER BY avg_refund_usd DESC;

-- D11. Products whose returns rose from the first half to the second half of
--      the dataset's date range (simple trend check without a full series).
WITH date_bounds AS (SELECT MIN(date_key) AS min_dk, MAX(date_key) AS max_dk FROM FactSales),
     midpoint AS (SELECT (min_dk + max_dk) / 2 AS mid_dk FROM date_bounds)
SELECT p.product_name,
       SUM(CASE WHEN fr.date_key <= m.mid_dk THEN 1 ELSE 0 END) AS returns_first_half,
       SUM(CASE WHEN fr.date_key > m.mid_dk THEN 1 ELSE 0 END) AS returns_second_half
FROM FactReturns fr
JOIN DimProduct p ON fr.product_key = p.product_key
CROSS JOIN midpoint m
GROUP BY p.product_name
HAVING returns_second_half > returns_first_half
ORDER BY (returns_second_half - returns_first_half) DESC LIMIT 15;

-- D12. Category revenue concentration: cumulative % of revenue (Pareto check).
SELECT category, revenue_usd,
       ROUND(SUM(revenue_usd) OVER (ORDER BY revenue_usd DESC) * 100.0
             / SUM(revenue_usd) OVER (), 2) AS cumulative_pct_of_revenue
FROM (SELECT p.category, SUM(fs.line_net_revenue_usd) AS revenue_usd
      FROM FactSales fs JOIN DimProduct p ON fs.product_key = p.product_key GROUP BY p.category)
ORDER BY revenue_usd DESC;

-- D13. Products priced above their category's average unit price but with
--      below-average category margin (potential mispricing candidates).
--     OPTIMIZED: the category averages are computed ONCE in CTEs. The naive
--     form used correlated subqueries in HAVING, re-scanning FactSales for
--     every product (10,000 times).
WITH product_margin AS (
    SELECT p.product_key, p.product_name, p.category, p.unit_price_usd,
           SUM(fs.line_gross_profit_usd) AS gp, SUM(fs.line_net_revenue_usd) AS rev
    FROM FactSales fs JOIN DimProduct p ON fs.product_key = p.product_key
    GROUP BY p.product_key, p.product_name, p.category, p.unit_price_usd
),
category_stats AS (
    SELECT category, AVG(unit_price_usd) AS avg_price, SUM(gp) / SUM(rev) AS category_margin
    FROM product_margin GROUP BY category
)
SELECT pm.product_name, pm.category, pm.unit_price_usd,
       ROUND(pm.gp / pm.rev, 4) AS product_margin_pct
FROM product_margin pm JOIN category_stats cs ON pm.category = cs.category
WHERE pm.unit_price_usd > cs.avg_price AND pm.gp / pm.rev < cs.category_margin
ORDER BY product_margin_pct ASC LIMIT 15;

-- D14. Supplier return-rate ranking (via DimProduct.supplier_id).
--      OPTIMIZED the same way as D1 (aggregate per product, then roll up).
SELECT p.supplier_id, SUM(s.lines_sold) AS lines_sold, SUM(COALESCE(r.returns, 0)) AS returns,
       ROUND(SUM(COALESCE(r.returns, 0)) * 1.0 / SUM(s.lines_sold), 4) AS return_rate
FROM (SELECT product_key, COUNT(*) AS lines_sold FROM FactSales GROUP BY product_key) s
JOIN DimProduct p ON p.product_key = s.product_key
LEFT JOIN (SELECT product_key, COUNT(*) AS returns FROM FactReturns GROUP BY product_key) r
    ON r.product_key = s.product_key
GROUP BY p.supplier_id
HAVING SUM(s.lines_sold) >= 50
ORDER BY return_rate DESC LIMIT 15;

-- D15. Top 10 products by absolute refund dollars (margin-recovery priority list).
SELECT p.product_name, p.category, ROUND(SUM(fr.refund_amount_usd), 2) AS total_refund_usd
FROM FactReturns fr JOIN DimProduct p ON fr.product_key = p.product_key
GROUP BY p.product_name, p.category ORDER BY total_refund_usd DESC LIMIT 10;


-- ============================================================
-- E. SHIPPING & LOGISTICS: WORST WAREHOUSE, SLOWEST COUNTRY, BOTTLENECKS
-- ============================================================

-- E1. Worst warehouse by average delivery delay (100+ shipments, to avoid
--     small-sample noise).
SELECT w.warehouse_id, w.warehouse_name, COUNT(*) AS shipments,
       ROUND(AVG(fsh.delivery_delay_days), 2) AS avg_delay_days
FROM FactShipping fsh JOIN DimWarehouse w ON fsh.origin_warehouse_key = w.warehouse_key
GROUP BY w.warehouse_id, w.warehouse_name
HAVING shipments >= 100
ORDER BY avg_delay_days DESC LIMIT 10;

-- E2. Slowest destination country by average delivery delay.
SELECT co.country_name, COUNT(*) AS shipments, ROUND(AVG(fsh.delivery_delay_days), 2) AS avg_delay_days
FROM FactShipping fsh JOIN DimCountry co ON fsh.destination_country_key = co.country_key
GROUP BY co.country_name ORDER BY avg_delay_days DESC LIMIT 10;

-- E3. Shipping bottlenecks: warehouse x destination-country pairs with the
--     worst combination of volume AND delay (a "fix this lane first" list).
SELECT w.warehouse_id, co.country_name, COUNT(*) AS shipments,
       ROUND(AVG(fsh.delivery_delay_days), 2) AS avg_delay_days,
       ROUND(COUNT(*) * AVG(fsh.delivery_delay_days), 2) AS delay_volume_score
FROM FactShipping fsh
JOIN DimWarehouse w ON fsh.origin_warehouse_key = w.warehouse_key
JOIN DimCountry co ON fsh.destination_country_key = co.country_key
GROUP BY w.warehouse_id, co.country_name
HAVING shipments >= 20
ORDER BY delay_volume_score DESC LIMIT 20;

-- E4. % of shipments delayed, by logistics partner.
SELECT partner_id, COUNT(*) AS shipments,
       ROUND(AVG(CASE WHEN is_delayed THEN 1.0 ELSE 0 END), 4) AS pct_delayed,
       ROUND(AVG(delivery_delay_days), 2) AS avg_delay_days
FROM FactShipping GROUP BY partner_id
HAVING shipments >= 50
ORDER BY pct_delayed DESC LIMIT 15;

-- E5. Route-level delay ranking (RANK) within each destination country.
SELECT country_name, route_id, avg_delay_days,
       RANK() OVER (PARTITION BY country_name ORDER BY avg_delay_days DESC) AS delay_rank_in_country
FROM (
    SELECT co.country_name, fsh.route_id, ROUND(AVG(fsh.delivery_delay_days), 2) AS avg_delay_days
    FROM FactShipping fsh JOIN DimCountry co ON fsh.destination_country_key = co.country_key
    GROUP BY co.country_name, fsh.route_id
) t
ORDER BY country_name, delay_rank_in_country LIMIT 100;

-- E6. On-time delivery rate by warehouse (lowest first).
SELECT w.warehouse_id, w.warehouse_name,
       ROUND(AVG(CASE WHEN fsh.delivery_delay_days <= 0 THEN 1.0 ELSE 0 END), 4) AS on_time_rate
FROM FactShipping fsh JOIN DimWarehouse w ON fsh.origin_warehouse_key = w.warehouse_key
GROUP BY w.warehouse_id, w.warehouse_name ORDER BY on_time_rate ASC LIMIT 15;

-- E7. Severe delays (15+ days): which warehouse/country lanes they cluster in.
SELECT w.warehouse_id, co.country_name, COUNT(*) AS severe_delay_shipments
FROM FactShipping fsh
JOIN DimWarehouse w ON fsh.origin_warehouse_key = w.warehouse_key
JOIN DimCountry co ON fsh.destination_country_key = co.country_key
WHERE fsh.delivery_delay_days >= 15
GROUP BY w.warehouse_id, co.country_name
ORDER BY severe_delay_shipments DESC LIMIT 15;

-- E8. Monthly average delivery delay trend (is logistics performance improving?).
SELECT d.year, d.month, ROUND(AVG(fsh.delivery_delay_days), 2) AS avg_delay_days, COUNT(*) AS shipments
FROM FactShipping fsh JOIN DimDate d ON fsh.date_key = d.date_key
GROUP BY d.year, d.month ORDER BY d.year, d.month;

-- E9. Delay variability by route: unpredictable lanes can hurt customer trust
--     more than consistently-slow ones.
SELECT route_id, COUNT(*) AS shipments,
       ROUND(AVG(delivery_delay_days), 2) AS avg_delay,
       ROUND(AVG(delivery_delay_days * delivery_delay_days) - AVG(delivery_delay_days) * AVG(delivery_delay_days), 2) AS delay_variance
FROM FactShipping GROUP BY route_id
HAVING shipments >= 20
ORDER BY delay_variance DESC LIMIT 15;

-- E10. Shipping status breakdown.
SELECT shipping_status, COUNT(*) AS shipments,
       ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM FactShipping), 2) AS pct_of_shipments
FROM FactShipping GROUP BY shipping_status ORDER BY shipments DESC;

-- E11. Countries whose average delay changed quarter over quarter (LAG).
SELECT country_name, year, quarter, avg_delay_days,
       ROUND(avg_delay_days - LAG(avg_delay_days) OVER (
           PARTITION BY country_name ORDER BY year, quarter), 2) AS qoq_change
FROM (
    SELECT co.country_name, d.year, d.quarter, ROUND(AVG(fsh.delivery_delay_days), 2) AS avg_delay_days
    FROM FactShipping fsh
    JOIN DimDate d ON fsh.date_key = d.date_key
    JOIN DimCountry co ON fsh.destination_country_key = co.country_key
    GROUP BY co.country_name, d.year, d.quarter
) t
ORDER BY country_name, year, quarter;

-- E12. Fastest warehouse-partner pairs - worth routing MORE volume through.
SELECT w.warehouse_id, fsh.partner_id, COUNT(*) AS shipments,
       ROUND(AVG(fsh.delivery_delay_days), 2) AS avg_delay_days
FROM FactShipping fsh JOIN DimWarehouse w ON fsh.origin_warehouse_key = w.warehouse_key
GROUP BY w.warehouse_id, fsh.partner_id
HAVING shipments >= 20
ORDER BY avg_delay_days ASC LIMIT 15;

-- E13. Delay distribution buckets.
SELECT
    CASE WHEN delivery_delay_days <= 0 THEN 'Early/On-time'
         WHEN delivery_delay_days <= 3 THEN 'Minor (1-3d)'
         WHEN delivery_delay_days <= 7 THEN 'Moderate (4-7d)'
         WHEN delivery_delay_days <= 14 THEN 'Major (8-14d)'
         ELSE 'Severe (15d+)' END AS delay_bucket,
    COUNT(*) AS shipments
FROM FactShipping GROUP BY delay_bucket ORDER BY shipments DESC;

-- E14. Warehouses with above-average shipment volume AND above-average delay
--      (the "under strain" list - candidates for added capacity).
WITH wh_stats AS (
    SELECT w.warehouse_id, w.warehouse_name, COUNT(*) AS shipments,
           AVG(fsh.delivery_delay_days) AS avg_delay
    FROM FactShipping fsh JOIN DimWarehouse w ON fsh.origin_warehouse_key = w.warehouse_key
    GROUP BY w.warehouse_id, w.warehouse_name
),
overall_avg AS (SELECT AVG(delivery_delay_days) AS overall_avg_delay FROM FactShipping)
SELECT wh.warehouse_id, wh.warehouse_name, wh.shipments, ROUND(wh.avg_delay, 2) AS avg_delay_days
FROM wh_stats wh CROSS JOIN overall_avg
WHERE wh.avg_delay > overall_avg.overall_avg_delay
  AND wh.shipments > (SELECT AVG(shipments) FROM wh_stats)
ORDER BY wh.shipments DESC, wh.avg_delay DESC LIMIT 15;

-- E15. Refund dollars on orders whose shipment was delayed, by country
--      (connects a logistics problem directly to a P&L number).
SELECT co.country_name, ROUND(SUM(fr.refund_amount_usd), 2) AS refund_from_delayed_orders_usd
FROM FactShipping fsh
JOIN DimCountry co ON fsh.destination_country_key = co.country_key
JOIN FactReturns fr ON fr.order_id = fsh.order_id
WHERE fsh.is_delayed = 1
GROUP BY co.country_name ORDER BY refund_from_delayed_orders_usd DESC LIMIT 15;


-- ============================================================
-- F. WAREHOUSE PERFORMANCE
-- ============================================================

-- F1. Shipment volume by warehouse.
SELECT w.warehouse_id, w.warehouse_name, w.warehouse_type, COUNT(*) AS shipments
FROM FactShipping fsh JOIN DimWarehouse w ON fsh.origin_warehouse_key = w.warehouse_key
GROUP BY w.warehouse_id, w.warehouse_name, w.warehouse_type ORDER BY shipments DESC;

-- F2. Warehouses ranked worst-to-best by average delay.
SELECT w.warehouse_id, w.warehouse_name,
       COUNT(*) AS shipments, ROUND(AVG(fsh.delivery_delay_days), 2) AS avg_delay,
       RANK() OVER (ORDER BY AVG(fsh.delivery_delay_days) DESC) AS worst_delay_rank
FROM FactShipping fsh JOIN DimWarehouse w ON fsh.origin_warehouse_key = w.warehouse_key
GROUP BY w.warehouse_id, w.warehouse_name
ORDER BY worst_delay_rank LIMIT 15;

-- F3. Warehouse type comparison - average delay by type.
SELECT w.warehouse_type, COUNT(*) AS shipments, ROUND(AVG(fsh.delivery_delay_days), 2) AS avg_delay_days
FROM FactShipping fsh JOIN DimWarehouse w ON fsh.origin_warehouse_key = w.warehouse_key
GROUP BY w.warehouse_type ORDER BY avg_delay_days DESC;

-- F4. Revenue fulfilled per warehouse vs. that warehouse's average delay
--     (are the busiest warehouses also the slowest?).
SELECT w.warehouse_id,
       ROUND(SUM(fs.line_net_revenue_usd), 2) AS revenue_fulfilled_usd,
       (SELECT ROUND(AVG(delivery_delay_days), 2) FROM FactShipping fsh
           WHERE fsh.origin_warehouse_key = w.warehouse_key) AS avg_delay_days
FROM FactSales fs JOIN DimWarehouse w ON fs.warehouse_key = w.warehouse_key
GROUP BY w.warehouse_id, w.warehouse_key ORDER BY revenue_fulfilled_usd DESC LIMIT 15;

-- F5. Warehouses by country (footprint check).
SELECT co.country_name, COUNT(*) AS num_warehouses
FROM DimWarehouse w JOIN DimCountry co ON w.country_key = co.country_key
GROUP BY co.country_name ORDER BY num_warehouses DESC;

-- F6. Shipment volume relative to capacity (a rough proxy using star-schema
--     data only - Phase 5's dim_warehouse_features.csv has the true
--     inventory-based utilization %).
SELECT w.warehouse_id, w.capacity_units, COUNT(fsh.shipping_key) AS shipments,
       ROUND(COUNT(fsh.shipping_key) * 1.0 / w.capacity_units * 1000000, 2) AS shipments_per_million_capacity
FROM DimWarehouse w LEFT JOIN FactShipping fsh ON w.warehouse_key = fsh.origin_warehouse_key
GROUP BY w.warehouse_id, w.capacity_units ORDER BY shipments_per_million_capacity DESC LIMIT 15;

-- F7. Warehouses with zero severe delays (15+ days) - the reliability benchmark set.
SELECT w.warehouse_id, w.warehouse_name, COUNT(*) AS shipments
FROM FactShipping fsh JOIN DimWarehouse w ON fsh.origin_warehouse_key = w.warehouse_key
GROUP BY w.warehouse_id, w.warehouse_name
HAVING SUM(CASE WHEN fsh.delivery_delay_days >= 15 THEN 1 ELSE 0 END) = 0 AND shipments >= 50
ORDER BY shipments DESC LIMIT 15;

-- F8. Warehouse-level return rate (returns on orders fulfilled there).
SELECT w.warehouse_id, COUNT(DISTINCT fs.order_id) AS orders_fulfilled,
       COUNT(DISTINCT fr.return_id) AS returns,
       ROUND(COUNT(DISTINCT fr.return_id) * 1.0 / COUNT(DISTINCT fs.order_id), 4) AS return_rate
FROM FactSales fs
JOIN DimWarehouse w ON fs.warehouse_key = w.warehouse_key
LEFT JOIN FactReturns fr ON fr.order_id = fs.order_id
GROUP BY w.warehouse_id
HAVING orders_fulfilled >= 100
ORDER BY return_rate DESC LIMIT 15;


-- ============================================================
-- G. COUNTRY / REGION ANALYSIS
-- ============================================================

-- G1. Full country scorecard: revenue, margin, orders, returns, avg delay.
SELECT co.country_name, co.region_name,
       COUNT(DISTINCT fs.order_id) AS orders,
       ROUND(SUM(fs.line_net_revenue_usd), 2) AS revenue_usd,
       ROUND(SUM(fs.line_gross_profit_usd) / SUM(fs.line_net_revenue_usd), 4) AS gross_margin_pct,
       (SELECT ROUND(AVG(delivery_delay_days), 2) FROM FactShipping fsh
           WHERE fsh.destination_country_key = co.country_key) AS avg_delay_days
FROM FactSales fs JOIN DimCountry co ON fs.country_key = co.country_key
GROUP BY co.country_name, co.region_name, co.country_key ORDER BY revenue_usd DESC;

-- G2. Region-level margin comparison.
SELECT co.region_name,
       ROUND(SUM(fs.line_gross_profit_usd) / SUM(fs.line_net_revenue_usd), 4) AS gross_margin_pct
FROM FactSales fs JOIN DimCountry co ON fs.country_key = co.country_key
GROUP BY co.region_name ORDER BY gross_margin_pct DESC;

-- G3. Countries with the highest return rate (order-level).
SELECT co.country_name,
       COUNT(DISTINCT fs.order_id) AS orders,
       COUNT(DISTINCT fr.order_id) AS returned_orders,
       ROUND(COUNT(DISTINCT fr.order_id) * 1.0 / COUNT(DISTINCT fs.order_id), 4) AS return_rate
FROM FactSales fs
JOIN DimCountry co ON fs.country_key = co.country_key
LEFT JOIN FactReturns fr ON fr.order_id = fs.order_id
GROUP BY co.country_name ORDER BY return_rate DESC LIMIT 15;

-- G4. Currency mix: revenue by currency code (via country -> currency).
SELECT co.currency_code, ROUND(SUM(fs.line_net_revenue_usd), 2) AS revenue_usd
FROM FactSales fs JOIN DimCountry co ON fs.country_key = co.country_key
GROUP BY co.currency_code ORDER BY revenue_usd DESC;

-- G5. Countries ranked by revenue per customer (market depth vs. breadth).
SELECT co.country_name,
       COUNT(DISTINCT fs.customer_key) AS customers,
       ROUND(SUM(fs.line_net_revenue_usd) / COUNT(DISTINCT fs.customer_key), 2) AS revenue_per_customer
FROM FactSales fs JOIN DimCountry co ON fs.country_key = co.country_key
GROUP BY co.country_name ORDER BY revenue_per_customer DESC LIMIT 15;

-- G6. Region x category revenue matrix (pivot-style cross-tab).
SELECT co.region_name, p.category, ROUND(SUM(fs.line_net_revenue_usd), 2) AS revenue_usd
FROM FactSales fs
JOIN DimCountry co ON fs.country_key = co.country_key
JOIN DimProduct p ON fs.product_key = p.product_key
GROUP BY co.region_name, p.category
ORDER BY co.region_name, revenue_usd DESC;

-- G7. Year-over-year revenue change by country (LAG on annual revenue).
SELECT country_name, year, revenue_usd,
       ROUND(revenue_usd - LAG(revenue_usd) OVER (PARTITION BY country_name ORDER BY year), 2) AS yoy_change_usd
FROM (
    SELECT co.country_name, d.year, SUM(fs.line_net_revenue_usd) AS revenue_usd
    FROM FactSales fs JOIN DimDate d ON fs.date_key = d.date_key
    JOIN DimCountry co ON fs.country_key = co.country_key
    GROUP BY co.country_name, d.year
) t
ORDER BY country_name, year;

-- G8. Countries with average delay above 3 days AND margin below the global
--     average (a compounded-risk shortlist).
SELECT co.country_name,
       (SELECT AVG(delivery_delay_days) FROM FactShipping fsh WHERE fsh.destination_country_key = co.country_key) AS avg_delay,
       ROUND(SUM(fs.line_gross_profit_usd) / SUM(fs.line_net_revenue_usd), 4) AS gross_margin_pct
FROM FactSales fs JOIN DimCountry co ON fs.country_key = co.country_key
GROUP BY co.country_name, co.country_key
HAVING avg_delay > 3
   AND gross_margin_pct < (SELECT SUM(line_gross_profit_usd) / SUM(line_net_revenue_usd) FROM FactSales)
ORDER BY avg_delay DESC;

-- G9. Distinct products sold per country (catalog reach).
SELECT co.country_name, COUNT(DISTINCT fs.product_key) AS distinct_products_sold
FROM FactSales fs JOIN DimCountry co ON fs.country_key = co.country_key
GROUP BY co.country_name ORDER BY distinct_products_sold DESC;

-- G10. Country rank by gross profit (RANK).
SELECT country_name, gross_profit_usd,
       RANK() OVER (ORDER BY gross_profit_usd DESC) AS profit_rank
FROM (
    SELECT co.country_name, ROUND(SUM(fs.line_gross_profit_usd), 2) AS gross_profit_usd
    FROM FactSales fs JOIN DimCountry co ON fs.country_key = co.country_key
    GROUP BY co.country_name
) t
ORDER BY profit_rank;


-- ============================================================
-- H. TIME-BASED TRENDS
-- ============================================================

-- H1. Daily revenue trend (full series).
SELECT d.full_date, ROUND(SUM(fs.line_net_revenue_usd), 2) AS revenue_usd
FROM FactSales fs JOIN DimDate d ON fs.date_key = d.date_key
GROUP BY d.full_date ORDER BY d.full_date;

-- H2. Weekly revenue trend.
SELECT d.year, strftime('%W', d.full_date) AS week_number, ROUND(SUM(fs.line_net_revenue_usd), 2) AS revenue_usd
FROM FactSales fs JOIN DimDate d ON fs.date_key = d.date_key
GROUP BY d.year, week_number ORDER BY d.year, week_number;

-- H3. Quarterly order count and revenue.
SELECT d.year, d.quarter, COUNT(DISTINCT fs.order_id) AS orders,
       ROUND(SUM(fs.line_net_revenue_usd), 2) AS revenue_usd
FROM FactSales fs JOIN DimDate d ON fs.date_key = d.date_key
GROUP BY d.year, d.quarter ORDER BY d.year, d.quarter;

-- H4. Month-over-month revenue growth rate (%).
SELECT year, month, revenue_usd,
       ROUND((revenue_usd - LAG(revenue_usd) OVER (ORDER BY year, month)) * 100.0
             / LAG(revenue_usd) OVER (ORDER BY year, month), 2) AS mom_growth_pct
FROM (SELECT d.year, d.month, SUM(fs.line_net_revenue_usd) AS revenue_usd
      FROM FactSales fs JOIN DimDate d ON fs.date_key = d.date_key GROUP BY d.year, d.month)
ORDER BY year, month;

-- H5. Best and worst single day by revenue.
SELECT 'Best' AS label, full_date, revenue_usd FROM (
    SELECT d.full_date, SUM(fs.line_net_revenue_usd) AS revenue_usd
    FROM FactSales fs JOIN DimDate d ON fs.date_key = d.date_key GROUP BY d.full_date
    ORDER BY revenue_usd DESC LIMIT 1
)
UNION ALL
SELECT 'Worst' AS label, full_date, revenue_usd FROM (
    SELECT d.full_date, SUM(fs.line_net_revenue_usd) AS revenue_usd
    FROM FactSales fs JOIN DimDate d ON fs.date_key = d.date_key GROUP BY d.full_date
    ORDER BY revenue_usd ASC LIMIT 1
);

-- H6. Weekend vs. weekday revenue comparison.
SELECT d.is_weekend, COUNT(DISTINCT fs.order_id) AS orders,
       ROUND(SUM(fs.line_net_revenue_usd), 2) AS revenue_usd,
       ROUND(SUM(fs.line_net_revenue_usd) / COUNT(DISTINCT fs.order_id), 2) AS avg_order_value_usd
FROM FactSales fs JOIN DimDate d ON fs.date_key = d.date_key
GROUP BY d.is_weekend;

-- H7. 30-day rolling revenue average (smooths daily noise).
SELECT full_date, revenue_usd,
       ROUND(AVG(revenue_usd) OVER (ORDER BY full_date ROWS BETWEEN 29 PRECEDING AND CURRENT ROW), 2) AS rolling_30d_avg
FROM (SELECT d.full_date, SUM(fs.line_net_revenue_usd) AS revenue_usd
      FROM FactSales fs JOIN DimDate d ON fs.date_key = d.date_key GROUP BY d.full_date)
ORDER BY full_date;

-- H8. Seasonality: average monthly revenue by calendar month, across years.
SELECT month, month_name, ROUND(AVG(monthly_rev), 2) AS avg_revenue_across_years
FROM (
    SELECT d.year, d.month, d.month_name, SUM(fs.line_net_revenue_usd) AS monthly_rev
    FROM FactSales fs JOIN DimDate d ON fs.date_key = d.date_key
    GROUP BY d.year, d.month, d.month_name
)
GROUP BY month, month_name ORDER BY month;

-- H9. Orders-per-day with a 7-day moving average (operational load view).
SELECT full_date, num_orders,
       ROUND(AVG(num_orders) OVER (ORDER BY full_date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW), 2) AS orders_7d_ma
FROM (SELECT d.full_date, COUNT(DISTINCT fs.order_id) AS num_orders
      FROM FactSales fs JOIN DimDate d ON fs.date_key = d.date_key GROUP BY d.full_date)
ORDER BY full_date;

-- H10. Recursive CTE: a complete daily calendar spine (including days with
--      ZERO orders) left-joined to revenue, so no gap days are silently
--      missing from a trend chart the way a plain GROUP BY would leave them.
WITH RECURSIVE date_spine(d) AS (
    SELECT MIN(full_date) FROM DimDate
    UNION ALL
    SELECT date(d, '+1 day') FROM date_spine WHERE d < (SELECT MAX(full_date) FROM DimDate)
)
SELECT ds.d AS calendar_date, COALESCE(ROUND(SUM(fs.line_net_revenue_usd), 2), 0) AS revenue_usd
FROM date_spine ds
LEFT JOIN DimDate dd ON date(dd.full_date) = ds.d
LEFT JOIN FactSales fs ON fs.date_key = dd.date_key
GROUP BY ds.d
ORDER BY ds.d
LIMIT 30;


-- ============================================================
-- I. DISCOUNTS
-- ============================================================

-- I1. Revenue and margin by order-level discount rate.
SELECT
    CASE WHEN order_discount_pct = 0 THEN 'No discount' ELSE printf('%.0f%%', order_discount_pct * 100) END AS discount_band,
    COUNT(DISTINCT order_id) AS orders,
    ROUND(SUM(line_net_revenue_usd), 2) AS revenue_usd,
    ROUND(SUM(line_gross_profit_usd), 2) AS gross_profit_usd
FROM FactSales GROUP BY discount_band ORDER BY revenue_usd DESC;

-- I2. Average order discount by customer segment.
SELECT c.segment, ROUND(AVG(fs.order_discount_pct), 4) AS avg_order_discount_pct
FROM (SELECT DISTINCT order_id, customer_key, order_discount_pct FROM FactSales) fs
JOIN DimCustomer c ON fs.customer_key = c.customer_key
GROUP BY c.segment;

-- I3. Products most frequently sold at a line-item discount.
SELECT p.product_name, COUNT(*) AS discounted_lines
FROM FactSales fs JOIN DimProduct p ON fs.product_key = p.product_key
WHERE fs.line_discount_pct > 0
GROUP BY p.product_name ORDER BY discounted_lines DESC LIMIT 15;

-- I4. Does discounting correlate with return rate? (order-level).
SELECT
    CASE WHEN fs.order_discount_pct = 0 THEN 'No discount' ELSE 'Discounted' END AS discount_band,
    COUNT(DISTINCT fs.order_id) AS orders,
    COUNT(DISTINCT fr.order_id) AS returned_orders,
    ROUND(COUNT(DISTINCT fr.order_id) * 1.0 / COUNT(DISTINCT fs.order_id), 4) AS return_rate
FROM FactSales fs LEFT JOIN FactReturns fr ON fr.order_id = fs.order_id
GROUP BY discount_band;

-- I5. Total discount dollars given up, by month.
SELECT d.year, d.month,
       ROUND(SUM(fs.line_total_usd - fs.line_net_revenue_usd), 2) AS order_discount_given_usd
FROM FactSales fs JOIN DimDate d ON fs.date_key = d.date_key
GROUP BY d.year, d.month ORDER BY d.year, d.month;

-- I6. Top 10 orders by order-level discount dollars given.
SELECT order_id, ROUND(SUM(line_total_usd - line_net_revenue_usd), 2) AS discount_usd
FROM FactSales GROUP BY order_id ORDER BY discount_usd DESC LIMIT 10;


-- ============================================================
-- J. ADVANCED / MISCELLANEOUS
-- ============================================================

-- J1. Customers who bought from more than 3 categories (cross-sell successes).
SELECT c.customer_id, COUNT(DISTINCT p.category) AS distinct_categories
FROM FactSales fs
JOIN DimCustomer c ON fs.customer_key = c.customer_key
JOIN DimProduct p ON fs.product_key = p.product_key
GROUP BY c.customer_id
HAVING distinct_categories > 3
ORDER BY distinct_categories DESC LIMIT 15;

-- J2. Products frequently bought together (market-basket pair counts within
--     the same order - the seed of a recommendation engine).
SELECT a.product_key AS product_a, b.product_key AS product_b, COUNT(*) AS times_bought_together
FROM FactSales a
JOIN FactSales b ON a.order_id = b.order_id AND a.product_key < b.product_key
GROUP BY a.product_key, b.product_key
ORDER BY times_bought_together DESC LIMIT 15;

-- J3. Top 3 countries by revenue each month (RANK recomputed monthly).
SELECT year, month, country_name, revenue_usd, rank_that_month FROM (
    SELECT year, month, country_name, revenue_usd,
           RANK() OVER (PARTITION BY year, month ORDER BY revenue_usd DESC) AS rank_that_month
    FROM (
        SELECT d.year, d.month, co.country_name, SUM(fs.line_net_revenue_usd) AS revenue_usd
        FROM FactSales fs JOIN DimDate d ON fs.date_key = d.date_key
        JOIN DimCountry co ON fs.country_key = co.country_key
        GROUP BY d.year, d.month, co.country_name
    )
) WHERE rank_that_month <= 3
ORDER BY year, month, rank_that_month;

-- J4. Gross margin percentile rank of every product (PERCENT_RANK) - a
--     normalized 0-1 score usable directly as a dashboard color scale.
SELECT product_id, ROUND(gross_margin_pct, 4) AS gross_margin_pct,
       ROUND(PERCENT_RANK() OVER (ORDER BY gross_margin_pct), 4) AS margin_percentile
FROM (
    SELECT p.product_id, SUM(fs.line_gross_profit_usd) / SUM(fs.line_net_revenue_usd) AS gross_margin_pct
    FROM FactSales fs JOIN DimProduct p ON fs.product_key = p.product_key GROUP BY p.product_id
)
ORDER BY margin_percentile DESC LIMIT 20;

-- J5. Orders with 5+ distinct products (a proxy for gift/bulk orders that may
--     warrant a different fulfillment SLA).
SELECT order_id, COUNT(DISTINCT product_key) AS distinct_products, SUM(quantity) AS total_units
FROM FactSales GROUP BY order_id
HAVING distinct_products >= 5
ORDER BY total_units DESC LIMIT 15;

-- J6. Executive one-pager: every headline KPI in a single row.
SELECT
    (SELECT COUNT(DISTINCT order_id) FROM FactSales) AS total_orders,
    (SELECT ROUND(SUM(line_net_revenue_usd), 2) FROM FactSales) AS total_revenue_usd,
    (SELECT ROUND(SUM(line_gross_profit_usd) / SUM(line_net_revenue_usd), 4) FROM FactSales) AS gross_margin_pct,
    (SELECT COUNT(*) FROM FactReturns) AS total_returns,
    (SELECT ROUND(AVG(delivery_delay_days), 2) FROM FactShipping) AS avg_delivery_delay_days,
    (SELECT ROUND(AVG(CASE WHEN is_delayed THEN 1.0 ELSE 0 END), 4) FROM FactShipping) AS pct_shipments_delayed;

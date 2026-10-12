-- ============================================================================
-- Phase 7 - Advanced SQL: Stored Procedures, Functions, Triggers (MySQL 8.0+)
-- ============================================================================
-- IMPORTANT: this file is MySQL-specific procedural SQL. SQLite has no stored
-- procedures or functions, and no MySQL server was available in the build
-- environment, so NOTHING in this file has been executed. It is written
-- against MySQL 8.0's documented syntax; treat it as unverified until you
-- run it on a real server:
--
--     mysql -u <user> -p ecommerce_supply_chain < sql/procedures.sql
--
-- (The analytical queries in window_queries.sql / business_queries.sql /
-- views.sql, by contrast, WERE executed - against the SQLite warehouse.)
-- ============================================================================

USE ecommerce_supply_chain;

-- ----------------------------------------------------------------------------
-- Supporting tables used by the procedures/triggers below
-- ----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS CountryProfitSnapshot (
    snapshot_id        BIGINT AUTO_INCREMENT PRIMARY KEY,
    snapshot_at        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    country_key        INT NOT NULL,
    orders             INT NOT NULL,
    revenue_usd        DECIMAL(16,2) NOT NULL,
    gross_profit_usd   DECIMAL(16,2) NOT NULL,
    gross_margin_pct   DECIMAL(6,4),
    INDEX idx_snapshot_country (country_key),
    CONSTRAINT fk_snapshot_country FOREIGN KEY (country_key) REFERENCES DimCountry(country_key)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS HighValueReturnLog (
    log_id             BIGINT AUTO_INCREMENT PRIMARY KEY,
    logged_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    return_id          VARCHAR(15) NOT NULL,
    order_id           VARCHAR(15) NOT NULL,
    refund_amount_usd  DECIMAL(12,2) NOT NULL,
    return_reason      VARCHAR(50)
) ENGINE=InnoDB;

DELIMITER $$

-- ----------------------------------------------------------------------------
-- FUNCTIONS
-- ----------------------------------------------------------------------------

-- Gross margin % from revenue and cost; NULL-safe, avoids divide-by-zero.
DROP FUNCTION IF EXISTS fn_gross_margin_pct$$
CREATE FUNCTION fn_gross_margin_pct(p_revenue DECIMAL(14,2), p_cost DECIMAL(14,2))
RETURNS DECIMAL(6,4)
DETERMINISTIC
BEGIN
    IF p_revenue IS NULL OR p_revenue = 0 THEN
        RETURN NULL;
    END IF;
    RETURN ROUND((p_revenue - IFNULL(p_cost, 0)) / p_revenue, 4);
END$$

-- Customer value tier from lifetime revenue. Thresholds are illustrative
-- and should be tuned to the business (see business_queries.sql C8 for the
-- quartile distribution that motivates them).
DROP FUNCTION IF EXISTS fn_customer_tier$$
CREATE FUNCTION fn_customer_tier(p_clv DECIMAL(14,2))
RETURNS VARCHAR(10)
DETERMINISTIC
BEGIN
    RETURN CASE
        WHEN p_clv IS NULL THEN 'Unknown'
        WHEN p_clv >= 20000 THEN 'Platinum'
        WHEN p_clv >= 10000 THEN 'Gold'
        WHEN p_clv >= 5000  THEN 'Silver'
        ELSE 'Bronze'
    END;
END$$

-- ----------------------------------------------------------------------------
-- STORED PROCEDURES
-- ----------------------------------------------------------------------------

-- One customer's headline numbers: orders, revenue, AOV, tier, first/last order.
DROP PROCEDURE IF EXISTS sp_customer_summary$$
CREATE PROCEDURE sp_customer_summary(IN p_customer_id VARCHAR(15))
BEGIN
    SELECT
        c.customer_id,
        COUNT(DISTINCT fs.order_id)                             AS num_orders,
        ROUND(SUM(fs.line_net_revenue_usd), 2)                  AS lifetime_revenue_usd,
        ROUND(SUM(fs.line_net_revenue_usd) / COUNT(DISTINCT fs.order_id), 2) AS avg_order_value_usd,
        fn_customer_tier(SUM(fs.line_net_revenue_usd))          AS value_tier,
        MIN(d.full_date)                                        AS first_order_date,
        MAX(d.full_date)                                        AS last_order_date,
        DATEDIFF(MAX(d.full_date), MIN(d.full_date))            AS tenure_days
    FROM FactSales fs
    JOIN DimCustomer c ON fs.customer_key = c.customer_key
    JOIN DimDate d     ON fs.date_key = d.date_key
    WHERE c.customer_id = p_customer_id
    GROUP BY c.customer_id;
END$$

-- Performance scorecard for one country, optionally limited to a year.
-- Pass NULL for p_year to include all years.
DROP PROCEDURE IF EXISTS sp_country_performance$$
CREATE PROCEDURE sp_country_performance(IN p_country_name VARCHAR(100), IN p_year SMALLINT)
BEGIN
    SELECT
        co.country_name,
        COUNT(DISTINCT fs.order_id)                               AS orders,
        ROUND(SUM(fs.line_net_revenue_usd), 2)                    AS revenue_usd,
        ROUND(SUM(fs.line_gross_profit_usd), 2)                   AS gross_profit_usd,
        fn_gross_margin_pct(SUM(fs.line_net_revenue_usd), SUM(fs.line_cost_usd)) AS gross_margin_pct
    FROM FactSales fs
    JOIN DimCountry co ON fs.country_key = co.country_key
    JOIN DimDate d     ON fs.date_key = d.date_key
    WHERE co.country_name = p_country_name
      AND (p_year IS NULL OR d.year = p_year)
    GROUP BY co.country_name;
END$$

-- Rebuilds the country profit snapshot table (intended for a nightly job or
-- MySQL EVENT). Runs in a transaction so readers never see a half-refreshed
-- snapshot; rolls back and re-raises on any error.
DROP PROCEDURE IF EXISTS sp_refresh_country_snapshot$$
CREATE PROCEDURE sp_refresh_country_snapshot()
BEGIN
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        RESIGNAL;
    END;

    START TRANSACTION;
        DELETE FROM CountryProfitSnapshot;
        INSERT INTO CountryProfitSnapshot
            (country_key, orders, revenue_usd, gross_profit_usd, gross_margin_pct)
        SELECT fs.country_key,
               COUNT(DISTINCT fs.order_id),
               ROUND(SUM(fs.line_net_revenue_usd), 2),
               ROUND(SUM(fs.line_gross_profit_usd), 2),
               fn_gross_margin_pct(SUM(fs.line_net_revenue_usd), SUM(fs.line_cost_usd))
        FROM FactSales fs
        GROUP BY fs.country_key;
    COMMIT;
END$$

-- Flags shipping lanes (origin warehouse x destination country) whose average
-- delay exceeds a threshold, returning the worst first. A parameterised
-- version of business_queries.sql E3 for reuse from an app or a Power BI
-- DirectQuery source.
DROP PROCEDURE IF EXISTS sp_shipping_bottlenecks$$
CREATE PROCEDURE sp_shipping_bottlenecks(IN p_min_shipments INT, IN p_min_avg_delay DECIMAL(6,2))
BEGIN
    SELECT w.warehouse_id, co.country_name,
           COUNT(*)                              AS shipments,
           ROUND(AVG(fsh.delivery_delay_days), 2) AS avg_delay_days
    FROM FactShipping fsh
    JOIN DimWarehouse w ON fsh.origin_warehouse_key = w.warehouse_key
    JOIN DimCountry co  ON fsh.destination_country_key = co.country_key
    GROUP BY w.warehouse_id, co.country_name
    HAVING COUNT(*) >= p_min_shipments AND AVG(fsh.delivery_delay_days) >= p_min_avg_delay
    ORDER BY avg_delay_days DESC;
END$$

-- ----------------------------------------------------------------------------
-- TRIGGERS
-- ----------------------------------------------------------------------------

-- Reject impossible sales rows at write time, complementing the CHECK
-- constraints in schema.sql with a clearer error message.
DROP TRIGGER IF EXISTS trg_factsales_before_insert$$
CREATE TRIGGER trg_factsales_before_insert
BEFORE INSERT ON FactSales
FOR EACH ROW
BEGIN
    IF NEW.quantity < 0 THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'FactSales: quantity cannot be negative';
    END IF;
    IF NEW.line_net_revenue_usd < 0 THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'FactSales: line_net_revenue_usd cannot be negative';
    END IF;
END$$

-- Audit trail: log any single return refunding more than $1,000 so finance
-- can review unusually large refunds without scanning FactReturns.
DROP TRIGGER IF EXISTS trg_factreturns_after_insert$$
CREATE TRIGGER trg_factreturns_after_insert
AFTER INSERT ON FactReturns
FOR EACH ROW
BEGIN
    IF NEW.refund_amount_usd > 1000 THEN
        INSERT INTO HighValueReturnLog (return_id, order_id, refund_amount_usd, return_reason)
        VALUES (NEW.return_id, NEW.order_id, NEW.refund_amount_usd, NEW.return_reason);
    END IF;
END$$

DELIMITER ;

-- Usage examples:
--   SELECT fn_gross_margin_pct(1000, 640);              -- 0.3600
--   SELECT fn_customer_tier(12500);                     -- 'Gold'
--   CALL sp_customer_summary('CUST0000001');
--   CALL sp_country_performance('Netherlands', 2024);
--   CALL sp_country_performance('Netherlands', NULL);
--   CALL sp_refresh_country_snapshot();
--   CALL sp_shipping_bottlenecks(50, 5.0);

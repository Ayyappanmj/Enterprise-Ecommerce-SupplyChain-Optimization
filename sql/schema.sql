-- ============================================================================
-- Enterprise E-Commerce Global Supply Chain & Margin Optimization
-- Phase 6 - MySQL Data Warehouse: star schema DDL
--
-- 5 dimension tables + 3 fact tables (Kimball style: facts at the lowest
-- useful grain, so Phase 7's SQL aggregates margin/delay/return metrics
-- rather than the warehouse pre-aggregating them).
--
-- Run against a real MySQL 8.0+ server with:
--     mysql -u <user> -p < sql/schema.sql
-- or let src/warehouse/mysql_loader.py run it for you (see README Phase 6).
-- ============================================================================

CREATE DATABASE IF NOT EXISTS ecommerce_supply_chain
    CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE ecommerce_supply_chain;

SET FOREIGN_KEY_CHECKS = 0;

DROP TABLE IF EXISTS FactReturns;
DROP TABLE IF EXISTS FactShipping;
DROP TABLE IF EXISTS FactSales;
DROP TABLE IF EXISTS DimWarehouse;
DROP TABLE IF EXISTS DimProduct;
DROP TABLE IF EXISTS DimCustomer;
DROP TABLE IF EXISTS DimCountry;
DROP TABLE IF EXISTS DimDate;

-- ----------------------------------------------------------------------------
-- Dimensions
-- ----------------------------------------------------------------------------

CREATE TABLE DimDate (
    date_key        INT PRIMARY KEY,               -- YYYYMMDD
    full_date       DATE NOT NULL UNIQUE,
    year            SMALLINT NOT NULL,
    quarter         TINYINT NOT NULL,
    month           TINYINT NOT NULL,
    month_name      VARCHAR(9) NOT NULL,
    day             TINYINT NOT NULL,
    day_of_week     TINYINT NOT NULL,               -- 0=Monday .. 6=Sunday
    day_name        VARCHAR(9) NOT NULL,
    is_weekend      BOOLEAN NOT NULL,
    CONSTRAINT chk_date_month CHECK (month BETWEEN 1 AND 12),
    CONSTRAINT chk_date_quarter CHECK (quarter BETWEEN 1 AND 4)
) ENGINE=InnoDB;

CREATE TABLE DimCountry (
    country_key     INT AUTO_INCREMENT PRIMARY KEY,
    country_id      VARCHAR(10) NOT NULL UNIQUE,     -- natural key from source (CTY001 ...)
    country_name    VARCHAR(100) NOT NULL,
    region_name     VARCHAR(50) NOT NULL,
    currency_code   CHAR(3) NOT NULL
) ENGINE=InnoDB;

CREATE TABLE DimCustomer (
    customer_key    INT AUTO_INCREMENT PRIMARY KEY,
    customer_id     VARCHAR(15) NOT NULL UNIQUE,
    first_name      VARCHAR(50),
    last_name       VARCHAR(50),
    email           VARCHAR(150),
    gender          VARCHAR(10),
    segment         VARCHAR(20),
    loyalty_tier    VARCHAR(20),
    country_key     INT,
    signup_date     DATE,
    CONSTRAINT fk_customer_country FOREIGN KEY (country_key)
        REFERENCES DimCountry(country_key) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB;

CREATE TABLE DimProduct (
    product_key     INT AUTO_INCREMENT PRIMARY KEY,
    product_id      VARCHAR(15) NOT NULL UNIQUE,
    product_name    VARCHAR(200),
    category        VARCHAR(50),
    sub_category    VARCHAR(50),
    supplier_id     VARCHAR(15),
    unit_cost_usd   DECIMAL(12,2) NOT NULL DEFAULT 0,
    unit_price_usd  DECIMAL(12,2) NOT NULL DEFAULT 0,
    CONSTRAINT chk_product_cost_nonneg CHECK (unit_cost_usd >= 0),
    CONSTRAINT chk_product_price_nonneg CHECK (unit_price_usd >= 0)
) ENGINE=InnoDB;

CREATE TABLE DimWarehouse (
    warehouse_key   INT AUTO_INCREMENT PRIMARY KEY,
    warehouse_id    VARCHAR(10) NOT NULL UNIQUE,
    warehouse_name  VARCHAR(150),
    warehouse_type  VARCHAR(50),
    country_key     INT,
    capacity_units  BIGINT NOT NULL DEFAULT 0,
    CONSTRAINT fk_warehouse_country FOREIGN KEY (country_key)
        REFERENCES DimCountry(country_key) ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT chk_warehouse_capacity_nonneg CHECK (capacity_units >= 0)
) ENGINE=InnoDB;

-- ----------------------------------------------------------------------------
-- Facts
-- ----------------------------------------------------------------------------

-- Grain: one row per order line item (order_item). Order- and country-level
-- revenue/margin are SQL aggregations over this table (see sql/business_queries.sql),
-- not pre-computed here, per standard star-schema design.
CREATE TABLE FactSales (
    sales_key           BIGINT AUTO_INCREMENT PRIMARY KEY,
    date_key            INT NOT NULL,
    order_id            VARCHAR(15) NOT NULL,        -- degenerate dimension
    order_item_id       VARCHAR(15) NOT NULL UNIQUE,
    customer_key        INT NOT NULL,
    product_key         INT NOT NULL,
    warehouse_key       INT NOT NULL,
    country_key         INT NOT NULL,
    order_status        VARCHAR(20),
    quantity            INT NOT NULL,
    unit_price_usd      DECIMAL(12,2) NOT NULL,
    unit_cost_usd       DECIMAL(12,2) NOT NULL,
    line_discount_pct   DECIMAL(5,4) NOT NULL DEFAULT 0,
    order_discount_pct  DECIMAL(5,4) NOT NULL DEFAULT 0,
    line_total_usd      DECIMAL(14,2) NOT NULL,
    line_net_revenue_usd DECIMAL(14,2) NOT NULL,
    line_cost_usd       DECIMAL(14,2) NOT NULL,
    line_gross_profit_usd DECIMAL(14,2) NOT NULL,
    line_shipping_cost_usd DECIMAL(14,2) NOT NULL DEFAULT 0,  -- order shipping cost allocated by line share of subtotal
    is_cross_border     BOOLEAN NOT NULL DEFAULT FALSE,       -- warehouse country <> destination country
    CONSTRAINT fk_sales_date FOREIGN KEY (date_key) REFERENCES DimDate(date_key),
    CONSTRAINT fk_sales_customer FOREIGN KEY (customer_key) REFERENCES DimCustomer(customer_key),
    CONSTRAINT fk_sales_product FOREIGN KEY (product_key) REFERENCES DimProduct(product_key),
    CONSTRAINT fk_sales_warehouse FOREIGN KEY (warehouse_key) REFERENCES DimWarehouse(warehouse_key),
    CONSTRAINT fk_sales_country FOREIGN KEY (country_key) REFERENCES DimCountry(country_key),
    CONSTRAINT chk_sales_quantity_nonneg CHECK (quantity >= 0)
) ENGINE=InnoDB;

CREATE INDEX idx_sales_date ON FactSales(date_key);
CREATE INDEX idx_sales_customer ON FactSales(customer_key);
CREATE INDEX idx_sales_product ON FactSales(product_key);
CREATE INDEX idx_sales_warehouse ON FactSales(warehouse_key);
CREATE INDEX idx_sales_country ON FactSales(country_key);
CREATE INDEX idx_sales_order ON FactSales(order_id);

-- Grain: one row per shipment.
CREATE TABLE FactShipping (
    shipping_key        BIGINT AUTO_INCREMENT PRIMARY KEY,
    date_key             INT NOT NULL,                -- ship date
    shipping_id          VARCHAR(15) NOT NULL UNIQUE,
    order_id             VARCHAR(15) NOT NULL,         -- degenerate dimension
    origin_warehouse_key INT NOT NULL,
    destination_country_key INT NOT NULL,
    partner_id           VARCHAR(10),                  -- degenerate dimension (no DimPartner in this model)
    route_id             VARCHAR(10),
    standard_transit_days INT,
    delivery_delay_days   INT,
    is_delayed            BOOLEAN NOT NULL DEFAULT FALSE,
    shipping_status       VARCHAR(30),
    CONSTRAINT fk_shipping_date FOREIGN KEY (date_key) REFERENCES DimDate(date_key),
    CONSTRAINT fk_shipping_warehouse FOREIGN KEY (origin_warehouse_key) REFERENCES DimWarehouse(warehouse_key),
    CONSTRAINT fk_shipping_country FOREIGN KEY (destination_country_key) REFERENCES DimCountry(country_key)
) ENGINE=InnoDB;

CREATE INDEX idx_shipping_date ON FactShipping(date_key);
CREATE INDEX idx_shipping_warehouse ON FactShipping(origin_warehouse_key);
CREATE INDEX idx_shipping_country ON FactShipping(destination_country_key);
CREATE INDEX idx_shipping_order ON FactShipping(order_id);
CREATE INDEX idx_shipping_delay ON FactShipping(delivery_delay_days);

-- Grain: one row per return event.
CREATE TABLE FactReturns (
    return_key          BIGINT AUTO_INCREMENT PRIMARY KEY,
    date_key             INT NOT NULL,                 -- return date
    return_id            VARCHAR(15) NOT NULL UNIQUE,
    order_id             VARCHAR(15) NOT NULL,
    product_key          INT NOT NULL,
    customer_key         INT NOT NULL,
    warehouse_key        INT NOT NULL,                 -- carried from the original order
    country_key          INT NOT NULL,                 -- destination country of the original order
    return_reason         VARCHAR(50),
    return_status         VARCHAR(20),
    return_condition      VARCHAR(30),
    refund_amount_usd     DECIMAL(12,2) NOT NULL DEFAULT 0,
    is_cross_border       BOOLEAN NOT NULL DEFAULT FALSE,
    CONSTRAINT fk_returns_date FOREIGN KEY (date_key) REFERENCES DimDate(date_key),
    CONSTRAINT fk_returns_product FOREIGN KEY (product_key) REFERENCES DimProduct(product_key),
    CONSTRAINT fk_returns_customer FOREIGN KEY (customer_key) REFERENCES DimCustomer(customer_key),
    CONSTRAINT fk_returns_warehouse FOREIGN KEY (warehouse_key) REFERENCES DimWarehouse(warehouse_key),
    CONSTRAINT fk_returns_country FOREIGN KEY (country_key) REFERENCES DimCountry(country_key),
    CONSTRAINT chk_returns_refund_nonneg CHECK (refund_amount_usd >= 0)
) ENGINE=InnoDB;

CREATE INDEX idx_returns_date ON FactReturns(date_key);
CREATE INDEX idx_returns_product ON FactReturns(product_key);
CREATE INDEX idx_returns_customer ON FactReturns(customer_key);
CREATE INDEX idx_returns_warehouse ON FactReturns(warehouse_key);
CREATE INDEX idx_returns_country ON FactReturns(country_key);
CREATE INDEX idx_returns_order ON FactReturns(order_id);

SET FOREIGN_KEY_CHECKS = 1;

# Changelog / Build Log

This is the detailed, phase-by-phase build journal for this project — what
was built, what was actually run and verified versus what's written-but-
untested, every real bug found along the way and how it was fixed, and every
honest caveat about synthetic data or missing infrastructure (no MySQL
server, no Power BI Desktop, no network access for installing some packages).

For a high-level overview, start with [README.md](README.md) instead. This
file is for anyone who wants the full detail behind a specific claim in the
README, or who's curious how the project actually got built, phase by phase.

---

## Phase 1 — Enterprise Data Generation

Generates a full synthetic e-commerce + global logistics dataset, entirely offline
(no API keys, no internet access, no Faker dependency — just pandas + numpy).

### Tables produced (`data/raw/*.csv`)

| Table | Full-scale rows | Notes |
|---|---:|---|
| regions | 5 | |
| countries | 30 | FK -> regions |
| currencies | 26 | |
| exchange_rates | ~19,000 | daily rate to USD per currency, 2 years |
| customers | 50,000 | FK -> countries |
| suppliers | 2,000 | FK -> countries |
| products | 10,000 | FK -> suppliers |
| warehouses | 150 | FK -> countries, regions |
| logistics_partners | 100 | FK -> countries |
| shipping_routes | 300 | FK -> warehouses, countries, partners |
| orders | 500,000 | FK -> customers, warehouses, countries |
| order_items | ~1.5M | FK -> orders, products |
| inventory | ~272,000 | FK -> warehouses, products |
| shipping | ~445,000 | FK -> orders, routes, partners |
| returns | 75,000 | FK -> orders, order_items |
| payments | 500,000 | FK -> orders |
| marketing_campaigns | 500 | FK -> regions, countries |

All target scale numbers from the project spec (500K orders, 50K customers,
10K products, 5 regions, 30 countries, 150 warehouses, 300 routes,
100 logistics partners, 75K returns) are met.

### Run it

```bash
pip install -r requirements.txt

# Full production-scale dataset (~250MB, ~15s on a laptop)
python -m src.data_generation.run_all

# Small/fast dataset for developing downstream ETL/SQL code
DATA_SCALE=sample python -m src.data_generation.run_all
```

Output lands in `data/raw/`.

### Design notes

- **Deterministic**: seeded RNG (`SEED = 42` in `config.py`) — reruns are reproducible.
- **Vectorized**: all generation uses numpy array ops / pandas, not row-by-row loops,
  so 500K orders + 1.5M order line items generate in seconds.
- **No network dependency**: names/cities/currencies come from curated lists in
  `reference_data.py` rather than Faker or a web API, so it works in offline/CI
  environments and needs no extra packages beyond pandas/numpy.
- **Referential integrity**: every foreign key in a child table is sampled directly
  from the parent table's generated ID column, so joins are guaranteed to resolve.

### Folder structure so far

```
Enterprise-Ecommerce-SupplyChain-Optimization/
├── data/
│   ├── raw/            <- Phase 1 output CSVs land here
│   ├── processed/
│   └── warehouse/
├── src/
│   └── data_generation/
│       ├── config.py                            (scale + seed)
│       ├── reference_data.py                    (static name/geo/category pools)
│       ├── utils.py                              (shared helpers)
│       ├── generate_geo_currency.py             (Regions, Countries, Currencies, Exchange_Rates)
│       ├── generate_customers.py                (Customers)
│       ├── generate_products.py                 (Suppliers, Products)
│       ├── generate_logistics_network.py        (Warehouses, Logistics_Partners, Shipping_Routes)
│       ├── generate_orders.py                   (Orders, Order_Items)
│       ├── generate_inventory_shipping.py       (Inventory, Shipping)
│       ├── generate_returns_payments_marketing.py (Returns, Payments, Marketing_Campaigns)
│       └── run_all.py                            (orchestrator)
├── requirements.txt
└── README.md
```

## Phase 2 — Multi-Source ETL Pipeline

Three simulated sources feed one pipeline, each isolated so a failure in one
doesn't block the others:

| # | Source | Simulates | Incremental watermark |
|---|---|---|---|
| 1 | Web Orders CSV | e-commerce platform's order export | `order_date` |
| 2 | Inventory System CSV | warehouse inventory system nightly export | `last_restock_date` |
| 3 | Shipping API | third-party logistics provider's REST API | `ship_date` |

**Source 3 is a real running Flask app** (`shipping_api_server.py`) — paginated,
and deliberately returns `503` on ~8% of requests so the retry logic has a
genuine transient failure to recover from, not a mocked one.

Pipeline stages, per source: **extract** (only rows newer than the stored
watermark) → **validate** (schema check, dedupe, null-key check, impossible-value
check — bad rows are quarantined, not dropped silently) → **transform**
(standardize dtypes, tag with `_source_system` / `_ingested_at`) → **load**
(append to `data/processed/`, advance the watermark only on success).

### Run it

```bash
# 1. generate raw data if you haven't already
python -m src.data_generation.run_all

# 2. start the mock Shipping API (separate terminal, keep it running)
python -m src.etl.shipping_api_server

# 3. run the pipeline (loads all history the first time)
python -m src.etl.run_pipeline

# 4. simulate a new day's data landing in all 3 sources
python -m src.etl.simulate_new_arrivals

# 5. run again - watch it load ONLY the new rows (true incremental load)
python -m src.etl.run_pipeline

# run a subset of sources
python -m src.etl.run_pipeline --sources web_orders inventory
```

Logs: `logs/etl.log` (also echoed to console). Watermarks:
`data/processed/_state/etl_state.json`. Quarantined rows:
`data/processed/rejected/<table>_rejected_<timestamp>.csv`.

### Reliability features implemented

- **Logging** — every extract/validate/load step logs to both file and console
  (`src/utils/logging_setup.py`).
- **Exception handling** — a custom exception hierarchy
  (`ExtractionError`, `TransientAPIError`, `ValidationError`, `LoadError`) lets
  the orchestrator tell "retry this" apart from "abort this source"; each
  source runs in its own try/except so one broken source never blocks the others.
- **Retry mechanism** — `src/utils/retry.py` is a generic exponential-backoff
  decorator (with jitter) applied to every Shipping API page fetch; verified
  live against the mock API's injected 503s.
- **Data validation** — `src/etl/validators.py` checks required columns,
  duplicate primary keys, null foreign keys, and impossible values (e.g.
  delivery date before ship date). Bad rows are quarantined to
  `data/processed/rejected/`, not dropped or allowed to poison the load.
- **Incremental loading** — a JSON watermark file per source
  (`src/etl/state_manager.py`) means every run only extracts/loads what's
  new since the last successful run; verified end-to-end with
  `simulate_new_arrivals.py`.

### Folder additions

```
src/etl/
├── config.py                       (paths, API host/port, retry settings)
├── exceptions.py                   (ETLError hierarchy)
├── state_manager.py                (JSON watermark persistence)
├── validators.py                   (per-table validation + quarantine)
├── transform.py                    (dtype standardization + ingestion tags)
├── load.py                         (incremental append + quarantine writer)
├── extract_web_orders.py           (Source 1)
├── extract_inventory.py            (Source 2)
├── shipping_api_server.py          (Source 3 - the fake Flask REST API itself)
├── extract_shipping_api.py         (Source 3 client, with retry/backoff)
├── simulate_new_arrivals.py        (appends "new" rows to raw/ for incremental demo)
└── run_pipeline.py                 (orchestrator / CLI entrypoint)
src/utils/
├── logging_setup.py
└── retry.py
logs/etl.log
```

## Phase 3 — Cloud Storage

Uploads `data/raw/`, `data/processed/`, and `data/processed/rejected/` to a
cloud bucket, organized as a small data lake:

```
<bucket>/
├── raw/<table>.csv                                  (latest full snapshot, overwritten in place)
├── processed/<table>/<table>_<UPLOADED_AT_UTC>.csv   (timestamped - never clobbered)
└── rejected/<table>/<original_filename>              (quarantined rows, for audit)
```

Three interchangeable providers behind one interface (`src/cloud/base_uploader.py`):
**GCS**, **S3**, and a zero-dependency **dry_run** mode that "uploads" to a local
folder (`cloud_mock_bucket/`) — useful for developing/demoing the pipeline
without a cloud account, and what this repo was built and tested against
(no cloud credentials were available in the build environment).

> ⚠️ **The GCS and S3 code paths are written against their real, documented
> SDK APIs (bucket creation, `blob.upload_from_filename` / `upload_file`,
> retry-worthy exceptions) but could not be executed against a live bucket
> here** — no cloud credentials or outbound network access were available.
> The **dry_run** provider *was* run end-to-end and is what the commands
> below demonstrate. Point `CLOUD_PROVIDER` at `gcs` or `s3` with real
> credentials (see `.env.example`) to use a real bucket; the upload logic,
> folder layout, retry behavior, and CLI are otherwise identical.

### Run it

```bash
# no setup needed - simulates a bucket at ./cloud_mock_bucket/
python -m src.cloud.run_upload --provider dry_run --bucket my-demo-bucket

# real Google Cloud Storage
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
export GCP_PROJECT_ID=your-project-id
python -m src.cloud.run_upload --provider gcs --bucket your-bucket-name

# real AWS S3
export AWS_ACCESS_KEY_ID=... AWS_SECRET_ACCESS_KEY=... AWS_REGION=us-east-1
python -m src.cloud.run_upload --provider s3 --bucket your-bucket-name

# upload only one category, or force re-upload of files already present
python -m src.cloud.run_upload --only processed
python -m src.cloud.run_upload --no-skip-existing
```

### What's implemented

- **Bucket creation** — `ensure_bucket_exists()` is idempotent for all three
  providers: checks first, creates only if missing.
- **Authentication** — GCS via `GOOGLE_APPLICATION_CREDENTIALS` service-account
  key (or Application Default Credentials); S3 via env vars or the standard
  `~/.aws/credentials` chain. See `.env.example`.
- **Upload with retry** — every real network call goes through the same
  `retry_with_backoff` decorator used in Phase 2, catching each SDK's own
  transient-error types (`GoogleAPIError` / `ClientError`).
- **Folder organization** — implemented in `upload_manager.build_upload_plan()`,
  shown above; verified against the dry_run bucket.
- **Skip-if-exists** — `object_exists()` avoids re-uploading raw files that
  haven't changed; verified (second run: 0 uploaded, 17 skipped).
- **Provider-agnostic** — swapping `dry_run` → `gcs`/`s3` is a config change
  only; `upload_manager.py` and the CLI never branch on provider.

### Folder additions

```
src/cloud/
├── config.py              (provider/bucket/credentials config, folder-prefix scheme)
├── base_uploader.py        (abstract interface)
├── dry_run_uploader.py     (local-folder stand-in - fully tested)
├── gcs_uploader.py         (real GCS implementation, lazy-imports google-cloud-storage)
├── s3_uploader.py          (real S3 implementation, lazy-imports boto3)
├── upload_manager.py       (provider factory + upload-plan builder + orchestration)
└── run_upload.py           (CLI entrypoint)
.env.example
cloud_mock_bucket/          (created at runtime by the dry_run provider; gitignored)
```

## Phase 4 — Data Cleaning

Cleans all 17 raw tables with pandas/numpy (no new dependencies), driven by a
declarative spec per table (`src/cleaning/table_specs.py`) so adding a new
table to the pipeline is a config entry, not new code.

| Requirement | Where |
|---|---|
| Duplicate removal | primary-key dedupe, every table |
| Null handling | rows missing a primary/foreign key are dropped; counted |
| Currency conversion | `orders.total_amount_usd` → `total_amount_local`, as-of join against `exchange_rates.csv` for the order's currency and date |
| Timezone normalization | `orders.order_date` → `order_date_utc`, treated as local time at the shipping country and converted to UTC |
| Negative quantity/amount detection | quantities, prices, costs, stock levels clipped to 0 if negative; counted |
| Impossible shipping dates | `shipping`: any delivery date earlier than its ship date is nulled out; counted |
| Outlier detection | Tukey's IQR (1.5×) on price/total/refund/delay columns — **flagged** in a `<col>_is_outlier` column, not deleted, since large-margin or heavily-delayed orders are exactly what this project investigates |
| Before/after reports | `reports/data_cleaning_summary.csv` + `reports/data_cleaning_report.md` |

### Run it

```bash
python -m src.data_generation.run_all      # if you haven't already
python -m src.cleaning.run_cleaning
```

Cleaned tables land in `data/processed/cleaned/<table>_clean.csv`. A worked
report from a full-scale run (500K orders etc.) ships in `reports/` as an
example.

### Verified, not just written

Since the synthetic data has no real duplicates/nulls/negatives by
construction, I injected known-bad rows into `order_items.csv` (1 exact
duplicate, 3 null `product_id`, 5 negative `quantity`) and re-ran the
cleaner — it reported exactly `dupes=1 nulls=3 negatives=5`, confirming the
detectors work rather than just running without error. A separate bug in
the currency as-of join (a `merge_asof` column-name mismatch) was caught the
same way and fixed before shipping.

### Folder additions

```
src/cleaning/
├── config.py            (paths, IQR multiplier, approximate country->UTC-offset map)
├── cleaning_utils.py     (vectorized primitives: dedupe, nulls, negatives, outliers, tz, FX)
├── table_specs.py        (declarative per-table cleaning rules)
├── cleaning_engine.py    (applies a spec to a table, produces a report row)
└── run_cleaning.py       (orchestrator - all 17 tables, writes reports)
data/processed/cleaned/
reports/data_cleaning_summary.csv
reports/data_cleaning_report.md
```

## Phase 5 — Feature Engineering

Builds every business metric the project spec asks for, on top of Phase 4's
cleaned tables, entirely with vectorized pandas/NumPy (groupby + merge +
array math — no per-row Python loops).

| Metric | Where | Definition |
|---|---|---|
| Gross Margin | `fact_order_features.csv` | (product revenue − COGS) / product revenue, per order |
| Net Margin | `fact_order_features.csv` | Gross profit − shipping cost − refunds − assumed opex, / revenue |
| Shipping Delay | `fact_shipping_features.csv` | `delivery_delay_days`, `is_delayed` flag, delay bucket |
| Warehouse Utilization | `dim_warehouse_features.csv` | total inventory units / warehouse capacity |
| Customer Lifetime Value | `dim_customer_features.csv` | historical (actual revenue to date) + a simple projected CLV for repeat customers |
| Average Order Value | `dim_customer_features.csv`, KPI summary | revenue / order count, per customer and overall |
| Repeat Purchase Rate | KPI summary | % of purchasing customers with 2+ orders |
| Return Rate | `dim_product_features.csv`, country summary, KPI summary | returned line items / sold line items |
| Profit by Country | `country_profit_summary.csv` | revenue, COGS, shipping, refunds, gross/net profit rolled up by ship country |

**Business assumptions are named constants, not magic numbers** — see
`src/feature_engineering/config.py`: an 8% operating-expense rate is assumed
for net margin (the dataset has no real overhead/warehousing cost line
items), and projected CLV uses a 3-year horizon and only computes a purchase
frequency for customers with 2+ orders.

### Run it

```bash
python -m src.data_generation.run_all        # if you haven't already
python -m src.cleaning.run_cleaning           # Phase 4
python -m src.feature_engineering.run_feature_engineering
```

Output: `data/processed/features/*.csv` plus `reports/kpi_summary.json` /
`.csv` (an example run's KPI summary and cleaning report ship in `reports/`).

### Verified, not just written

- Manually recomputed revenue/COGS/gross-profit for a specific order outside
  the pipeline and confirmed it matched the generated feature row exactly.
- **Caught and fixed a Phase 1 data-generation bug this phase exposed**:
  warehouse `capacity_units` had been generated far too small relative to
  the inventory volume Phase 1 also generates, so utilization initially came
  out at 2,000–12,000%. Fixed by resizing the capacity range in
  `src/data_generation/generate_logistics_network.py`; utilization now
  ranges a realistic 36%–143% (mean ~67%) across the 150 warehouses.
- On this dataset, `repeat_purchase_rate` comes out at ~99.96% — worth
  knowing before you show it to anyone: with 500K orders spread over only
  50K customers (~10 orders/customer on average), it's expected that nearly
  every customer has more than one order. That's a property of this
  synthetic data's order/customer ratio, not a data-quality bug.

### Folder additions

```
src/feature_engineering/
├── config.py               (paths + documented business assumptions)
├── data_loader.py           (loads Phase 4's cleaned tables)
├── order_features.py        (Gross Margin, Net Margin)
├── shipping_features.py     (Shipping Delay, Warehouse Utilization)
├── customer_features.py     (CLV, AOV, Repeat Purchase Rate)
├── product_features.py      (product margin, Return Rate)
├── country_features.py      (Profit by Country)
├── kpi_summary.py           (single-row executive rollup)
└── run_feature_engineering.py   (orchestrator)
data/processed/features/
reports/kpi_summary.json, kpi_summary.csv
```

## Phase 6 — MySQL Data Warehouse

A Kimball-style star schema: 5 dimensions + 3 facts, with the facts kept at
their lowest useful grain (order line item / shipment / return event) so
margin, delay, and return metrics are SQL aggregations (Phase 7), not
pre-computed here.

```
DimDate ─┐
DimCountry ─┼─→ FactSales (grain: order line item)
DimCustomer ─┤        also → FactShipping (grain: shipment)
DimProduct ─┤        also → FactReturns  (grain: return event)
DimWarehouse ┘
```

The canonical DDL — `sql/schema.sql` — is real MySQL 8.0+: `AUTO_INCREMENT`
surrogate keys, `ENGINE=InnoDB`, foreign keys with `ON DELETE`/`ON UPDATE`
behavior, and `CHECK` constraints (e.g. quantities/costs/refunds ≥ 0).

> ⚠️ **No MySQL server was available in the build environment** (no network
> access to install one, and none pre-installed), so `sql/schema.sql` and
> `mysql_loader.py` are written against MySQL's real, documented syntax but
> could not be executed against a live server here. What **was** built and
> fully tested is a second, zero-dependency path: `WAREHOUSE_ENGINE=sqlite`
> creates an equivalent schema (same tables/keys/grain, SQLite-flavored DDL)
> in a local file using nothing but Python's stdlib `sqlite3`, and
> `schema_builder.py` — the actual dimensional-modeling logic: surrogate
> keys, grain, joins — is 100% shared between both engines. Point
> `WAREHOUSE_ENGINE=mysql` at a real server (see `.env.example`) to use it
> for real; if something doesn't run cleanly, let me know and I'll fix it.

### Run it

```bash
python -m src.data_generation.run_all      # if you haven't already
python -m src.cleaning.run_cleaning        # Phase 4 (warehouse loads from cleaned data)

# local, zero-dependency (what this was tested with)
python -m src.warehouse.run_load_warehouse

# real MySQL
export MYSQL_HOST=... MYSQL_USER=... MYSQL_PASSWORD=... MYSQL_DATABASE=ecommerce_supply_chain
python -m src.warehouse.run_load_warehouse --engine mysql
```

### Verified, not just written

Loaded the full-scale dataset (500K orders → 1.5M `FactSales` rows, 445K
`FactShipping`, 75K `FactReturns`) end-to-end into SQLite in ~45s, then:

- **Zero orphaned fact rows** — every `FactSales` row's `customer_key` and
  `product_key` resolves to a real dimension row (checked with a `LEFT JOIN
  ... WHERE dim.key IS NULL` query).
- **Cross-phase reconciliation** — summed `FactSales.line_gross_profit_usd`
  and compared it against Phase 5's independently-computed
  `order_features.gross_profit_usd`. First attempt: **off by $51M** ($229M
  vs $178M), because `order_items.line_total_usd` only carries the
  item-level discount, not the order-level `discount_pct` — a real bug this
  cross-check caught. Fixed by allocating the order-level discount into the
  fact table (`line_net_revenue_usd`, `order_discount_pct` columns added to
  `FactSales`); the two now agree to **$10 on $178M** (0.00001%, plain
  per-line vs. per-order rounding noise).
- A sample business query (`SUM(line_gross_profit_usd) GROUP BY country`)
  runs correctly end-to-end and returns a sane top country.

### Folder additions

```
sql/schema.sql                    (canonical MySQL DDL - 5 dims + 3 facts, indexes, FKs, CHECKs)
src/warehouse/
├── config.py             (engine selection, MySQL connection params)
├── schema_builder.py      (DB-agnostic dim/fact builders - the tested dimensional-modeling logic)
├── sqlite_loader.py        (zero-dependency loader - what this was tested against)
├── mysql_loader.py         (real MySQL loader via SQLAlchemy+PyMySQL, lazy-imported)
└── run_load_warehouse.py   (orchestrator / CLI entrypoint)
data/warehouse/warehouse.db       (created at runtime; gitignored)
```

## Phase 7 — Advanced SQL

| File | Contents | Executed? |
|---|---|---|
| `sql/window_queries.sql` | 13 window-function queries: `ROW_NUMBER`, `RANK`, `DENSE_RANK`, `LEAD`, `LAG`, `NTILE`, `PERCENT_RANK`, `CUME_DIST`, `FIRST_VALUE`/`LAST_VALUE`, running totals, moving averages | ✅ against SQLite |
| `sql/business_queries.sql` | **107 numbered business queries** in 10 sections (revenue, margin, customers, products & returns, shipping, warehouses, countries, time trends, discounts, advanced) incl. CTEs and 2 recursive CTEs | ✅ against SQLite |
| `sql/views.sql` | 10 reusable views (order-line profitability, country/customer/product/warehouse performance, return hotspots, repeat customers, route delay, daily KPI) | ✅ against SQLite |
| `sql/procedures.sql` | 2 functions, 4 stored procedures, 2 triggers (MySQL 8.0 syntax) | ❌ **not executed** |
| `docs/sql_query_optimization.md` | Index explanation with measured before/after timings, and the query rewrites that fixed four slow queries | ✅ measured |

That is 120 analytical queries plus 10 views. The spec's named business
problems are all covered: worst warehouse (E1), slowest country (E2), highest-margin
products (B3), repeat customers (C3/C4), monthly retention (C11, a recursive-CTE
cohort curve), shipping bottlenecks (E3), and return hotspots (D4).

> ⚠️ **Three caveats you should know about.**
>
> **1. Dialect.** The queries were executed against the SQLite warehouse (no MySQL
> server was available). They use standard SQL plus a few SQLite functions that
> need MySQL equivalents: `strftime()` -> `DATE_FORMAT()`, `julianday()` differences
> -> `DATEDIFF()`, `date(x, '-90 days')` -> `DATE_SUB(x, INTERVAL 90 DAY)`,
> `printf()` -> `FORMAT()`/`CONCAT()`, and `WITH RECURSIVE` needs MySQL 8.0+.
>
> **2. `procedures.sql` has never been run.** SQLite has no stored procedures or
> functions, so the procedural file could not be tested at all. It is written
> against MySQL 8.0's documented syntax, but treat it as unverified until you run
> it on a real server.
>
> **3. The numbers are not findings.** The data is synthetic with random delays and
> margins, so e.g. the "worst warehouse" (2.67 days) barely differs from the average
> (~2.4). The SQL is the deliverable; don't quote the results as insights.

### Run it

```bash
python -m src.data_generation.run_all && python -m src.cleaning.run_cleaning
python -m src.warehouse.run_load_warehouse          # builds data/warehouse/warehouse.db

python -m src.warehouse.run_sql_file sql/views.sql
python -m src.warehouse.run_sql_file sql/window_queries.sql --show 3
python -m src.warehouse.run_sql_file sql/business_queries.sql --show 2 --timeout 30
```

### Verified, not just written

- Ran all 120 queries against the full-scale warehouse. **Zero failures.**
- **Caught and fixed a wrong-answer bug**: an early `LAG` query subtracted `date_key`
  integers (`20240201 - 20240131 = 70`, not 1 day). Rewritten with real dates.
- **Caught a stale file**: an earlier draft of `business_queries.sql` referenced view
  column names that no longer existed (10 of 58 statements failed). Replaced by the
  107-query version, which queries the fact tables directly.
- **Optimized four queries** (D1, D2, D13, D14) that exceeded an 8-second cutoff by
  aggregating each side before joining and replacing correlated subqueries with CTEs.
  All now pass; the slowest of the 107 is the market-basket self-join at ~7 s.
- **Measured the indexes**: selective lookups run ~3,800-5,900x faster with an index,
  but a low-selectivity filter (one country of 30) only ~4x - documented honestly in
  `docs/sql_query_optimization.md`.

### Folder additions

```
sql/window_queries.sql, business_queries.sql, views.sql, procedures.sql
src/warehouse/run_sql_file.py       (executes a .sql file, reports status/timing)
docs/sql_query_optimization.md
```

## Phase 8 — Power BI Executive Dashboard

> ⚠️ **Power BI Desktop is Windows-only GUI software and was not available in
> this (Linux, no-GUI) build environment**, so no `.pbix` file exists and
> nothing here has been visually verified. What's real: DAX written against
> Power BI's documented language, with every headline measure's expected
> value checked arithmetically against the actual warehouse (not guessed);
> a data model that matches Phase 6's star schema exactly; and precise,
> page-by-page build instructions. See `dashboards/README.md` for the full
> build guide, connection options (a tested CSV-export path needing no
> MySQL/ODBC setup at all), and every caveat. Assembling the actual file
> needs Power BI Desktop on your end — if something in here doesn't work as
> documented, tell me and I'll fix it.

**A real schema gap found while designing this phase**: `FactReturns` had no
country or warehouse key, so a "return rate by country" measure would have
silently shown the same global number for every country. Fixed by adding
`warehouse_key`/`country_key`/`is_cross_border` to `FactReturns` and
`line_shipping_cost_usd`/`is_cross_border` to `FactSales` (both `sql/schema.sql`
and the SQLite loader), then re-ran the full pipeline: zero orphaned rows, the
new shipping-cost column reconciles with Phase 5 to within $1.37 on $7M, and
all 120 Phase 7 SQL queries still pass against the patched schema.

Six pages specified: Executive Overview, Global Map, Warehouse Performance,
Shipping Intelligence, Customer Analytics, Profit Analysis — with DAX for
every KPI, drill-through, bookmark, and tooltip the spec asks for.

### Folder additions

```
dashboards/README.md              (full build guide, page-by-page spec, caveats)
dashboards/dax_measures.dax       (every DAX measure, checked against the warehouse)
src/warehouse/export_to_csv.py    (warehouse -> CSV, for a zero-driver Power BI connection)
```

## Phase 9 — Architecture Diagrams

Five diagrams (ETL Flow, Cloud Architecture, Warehouse Star Schema, Dashboard
Flow, Git Workflow), each shipped as editable Mermaid source plus rendered
SVG and PNG. Unlike most other phases, these were fully rendered and visually
inspected here — no server or credentials needed, just `mermaid-cli`.

See `architecture/README.md` for what each diagram shows and how to
regenerate them.

### Folder additions

```
architecture/
├── README.md
├── etl_flow.mmd / .svg / .png
├── cloud_architecture.mmd / .svg / .png
├── warehouse_star_schema.mmd / .svg / .png
├── dashboard_flow.mmd / .svg / .png
└── git_workflow.mmd / .svg / .png
```

## Phase 10 — Testing

**71 unit tests, 98.7% line coverage on the 10 modules tested, 0 failures.**
Actually run here — see `reports/test_coverage_report.md` for the full
breakdown, including the 6 lines that aren't covered and why.

```bash
python -m unittest discover -s tests -v      # 71 tests, ~0.4s, zero installs needed
```

Two honest adaptations, both because `pytest`/`coverage` couldn't be
installed in this build environment (no network access):

- **Tests are `unittest.TestCase` classes**, not pytest fixtures — pure
  stdlib, runs today with zero installs, *and* pytest auto-discovers and runs
  `unittest.TestCase` natively, so `pytest tests/` works unmodified once
  pytest is available (`pytest.ini` is included and ready).
- **Coverage measured with the stdlib `trace` module**, not `coverage.py` —
  real, measured line-execution numbers, just from a different tool.
  `tests/summarize_trace_coverage.py` turns `trace`'s raw output into the
  table in the report.

**A real bug found by these tests**: a deliberately adversarial test case
(revenue of exactly $0 with zero returns in the batch) crashed
`order_features.py` with `ZeroDivisionError` instead of producing `NaN`.
Root cause: `groupby().sum()` on an empty DataFrame returns `object` dtype,
and `fillna(0.0)` doesn't upcast it back to `float64` — so later division
silently fell back to pure-Python arithmetic, where `0.0/0.0` raises instead
of returning `inf`/`NaN` the way real NumPy float64 division does. Invisible
at full scale (real data always has returns, and no order is 100% discounted),
but a real crash waiting to happen on a smaller or filtered batch. Fixed with
an explicit `.astype(float)` in 3 places across `order_features.py` and
`shipping_features.py`; reran the full pipeline afterward to confirm no
change to real output values.

### Folder additions

```
tests/
├── test_cleaning_utils.py             (Phase 4: all 7 cleaning operations)
├── test_etl_validators.py             (Phase 2: dedupe/null/negative/date quarantine)
├── test_etl_retry_and_state.py        (Phase 2: retry backoff, watermark persistence)
├── test_etl_transform_and_load.py     (Phase 2: metadata tagging, incremental append)
├── test_feature_engineering.py        (Phase 5: margin/CLV math, found the ZeroDivisionError bug)
├── test_warehouse_schema_builder.py   (Phase 6/8: every dim/fact builder)
├── test_warehouse_sqlite_loader.py    (Phase 6: real SQLite I/O, FK integrity, CHECK constraints)
└── summarize_trace_coverage.py        (turns stdlib trace output into a coverage table)
pytest.ini
reports/test_coverage_report.md
```

## Phase 11 — Documentation

Split documentation into two documents with different readers: `README.md`
rewritten as a clean top-level overview (Problem Statement, Architecture,
Tech Stack, Screenshots, Results/KPIs, Business Impact, Folder Guide,
Installation, Known Limitations, Future Improvements), and this file
(`CHANGELOG.md`) keeping the full phase-by-phase verification detail that
used to live in the README.

Added 5 real matplotlib charts (`screenshots/`) generated by querying the
actual warehouse database — no Power BI file exists to screenshot (Phase 8),
so these are an honest substitute rather than a placeholder for something
that doesn't exist. Building them caught a real rendering bug: a chart title
containing two `$` signs ("$75,000 returns, $15.9M total") was silently
parsed as LaTeX math mode by matplotlib, italicizing the numbers between
them. Fixed by removing the second `$`. `screenshots/README.md` also flags
where the synthetic data's limitations show through directly in the charts
(near-uniform country revenue, a "Severe (15d+)" delay bucket that's
structurally always zero).

### Folder additions

```
CHANGELOG.md                  (this file - the full build log, split out of README.md)
screenshots/
├── README.md
├── 01_monthly_revenue_margin_trend.png
├── 02_top_countries_by_profit.png
├── 03_shipping_delay_distribution.png
├── 04_return_reasons.png
└── 05_warehouse_volume_vs_delay.png
```

## Phase 12 — GitHub Packaging

A real `git` repository with real, sequential commits — one per phase,
tagged `v0.1.0` through `v0.11.0` — plus `LICENSE` (MIT), an expanded
`.gitignore`, `RELEASE_NOTES.md`, and `GITHUB_SETUP.md` (suggested repo
description/topics, since those are GitHub repo *metadata*, not files, and
can't be set without a real GitHub repo existing).

**What "professional commit history" means here, precisely**: every commit
is real — a real diff, a real hash, matching that phase's actual content —
made in the single session this project was assembled in. That is NOT the
same claim as "built over N weeks of real development," and `GITHUB_SETUP.md`
says so explicitly rather than let the commit list imply a timeline that
didn't happen. The commit author is a placeholder
(`Your Name <you@example.com>`) with instructions for replacing it with a
real identity before pushing.

### Folder additions

```
LICENSE
RELEASE_NOTES.md
GITHUB_SETUP.md
.git/                  (real commit history, v0.1.0 .. v0.11.0 tags)
```

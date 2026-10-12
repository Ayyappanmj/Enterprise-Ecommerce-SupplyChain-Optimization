# Data Cleaning Report — Before / After

Tables processed: **17**  |  Total rows before: **3,384,060**  |  Total rows after: **3,384,060**

## Totals across all tables

- Duplicate rows removed: **0**
- Rows dropped for null primary/foreign keys: **0**
- Negative values clipped to 0: **0**
- Impossible dates corrected (end date nulled): **5,723**
- Statistical outliers flagged (kept, not deleted): **112,534**

## Per-table detail

| Table | Before | After | Dupes | Nulls Dropped | Negatives Fixed | Impossible Dates | Outliers Flagged | TZ Normalized | Currency Converted |
|---|---:|---:|---:|---:|---:|---:|---:|---|---|
| regions | 5 | 5 | 0 | 0 | 0 | 0 | 0 | — | — |
| countries | 30 | 30 | 0 | 0 | 0 | 0 | 0 | — | — |
| currencies | 26 | 26 | 0 | 0 | 0 | 0 | 0 | — | — |
| exchange_rates | 28,600 | 28,600 | 0 | 0 | 0 | 0 | 0 | — | — |
| customers | 50,000 | 50,000 | 0 | 0 | 0 | 0 | 0 | — | — |
| suppliers | 2,000 | 2,000 | 0 | 0 | 0 | 0 | 0 | — | — |
| products | 10,000 | 10,000 | 0 | 0 | 0 | 0 | 651 | — | — |
| warehouses | 150 | 150 | 0 | 0 | 0 | 0 | 0 | — | — |
| logistics_partners | 100 | 100 | 0 | 0 | 0 | 0 | 0 | — | — |
| shipping_routes | 300 | 300 | 0 | 0 | 0 | 0 | 0 | — | — |
| orders | 500,000 | 500,000 | 0 | 0 | 0 | 0 | 25549 | order_date | Yes |
| order_items | 1,500,216 | 1,500,216 | 0 | 0 | 0 | 0 | 72896 | — | — |
| inventory | 272,047 | 272,047 | 0 | 0 | 0 | 0 | 0 | — | — |
| shipping | 445,086 | 445,086 | 0 | 0 | 0 | 5723 | 0 | — | — |
| returns | 75,000 | 75,000 | 0 | 0 | 0 | 0 | 3847 | — | — |
| payments | 500,000 | 500,000 | 0 | 0 | 0 | 0 | 9580 | — | — |
| marketing_campaigns | 500 | 500 | 0 | 0 | 0 | 0 | 11 | — | — |

## Methodology notes

- **Duplicate removal**: exact duplicates on each table's primary key, first occurrence kept.
- **Null handling**: rows missing a primary key or a required foreign key are dropped (they can never join correctly downstream); non-critical nulls are left as-is for now.
- **Negative quantity/amount detection**: quantities, prices, costs and stock levels can never legitimately be negative; such values are clipped to 0 and counted.
- **Impossible shipping dates**: any `actual_delivery_date` or `promised_delivery_date` earlier than its `ship_date` is nulled out (delivery treated as unconfirmed) rather than dropping the whole shipment record.
- **Outlier detection**: Tukey's IQR method (1.5x IQR fences) per numeric column of interest. Outliers are **flagged** in a `<column>_is_outlier` column, not deleted - unusually large orders, refunds, or delays are exactly the signal a margin/delay investigation cares about.
- **Timezone normalization**: `orders.order_date` is treated as local time at the shipping country and converted to UTC (`order_date_utc`) using an approximate standard-time offset per country, so cross-region time-based analysis isn't skewed by local clocks.
- **Currency conversion**: `orders.total_amount_usd` is converted back to the order's local currency (`total_amount_local`) using the historical daily FX rate closest to (on or before) the order date, demonstrating an as-of currency join.
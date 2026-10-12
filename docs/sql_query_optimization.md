# SQL Query Optimization & Index Notes

All timings below were measured on the full-scale warehouse (1.5M `FactSales`
rows, 445K `FactShipping`, 75K `FactReturns`) using **SQLite 3.45** and
`EXPLAIN QUERY PLAN`. MySQL's optimizer differs in detail (use `EXPLAIN` /
`EXPLAIN ANALYZE` there), but the principles carry over. Absolute times will
vary by machine; the *ratios* are what matter.

## 1. Why the foreign-key indexes exist

Every fact table has an index on each foreign key (see `sql/schema.sql`).
Star-schema queries almost always filter or join a fact table on those keys,
and without an index the engine must scan every fact row.

| Query | With index | Without | Plan (with) | Speedup |
|---|---:|---:|---|---:|
| One order's line items (`order_id = ?`) | ~0 ms | 122 ms | `SEARCH FactSales USING INDEX idx_sales_order` | ~5,900x |
| One customer's history (`customer_key = ?`) | ~0 ms | 119 ms | `SEARCH ... idx_sales_customer` | ~4,900x |
| Severe delays (`delivery_delay_days >= 15`) | ~0 ms | 35 ms | `SEARCH ... COVERING INDEX idx_shipping_delay` | ~3,800x |
| All sales for one country (`country_key = ?`) | 32 ms | 133 ms | `SEARCH ... idx_sales_country` | **4x** |

**The last row is the important one.** An index is not a universal speedup: a
country holds roughly 1/30 of all sales rows, so the query still has to read
~50,000 rows and the index saves only a modest amount. Indexes pay off most
for *selective* predicates (one order, one customer). For low-selectivity
filters they help far less, and every index also costs disk space and slows
inserts — which is why the loaders in `src/warehouse/` build tables first and
this schema keeps to one index per foreign key rather than indexing everything.

"COVERING INDEX" (the shipping-delay row) means the index alone contained every
column the query needed, so the table itself was never touched.

## 2. Query rewrites that mattered

Running all 107 business queries at full scale surfaced four that exceeded an
8-second cutoff (D1, D2, D13, D14). All were fixed with the same two ideas,
and all four now finish well inside the limit.

**Aggregate each side first, then join.** The naive return-rate query joined
1.5M sales rows to returns and ran `COUNT(DISTINCT ...)` across the result.
Returns per product don't depend on the sales join at all, so the optimized
form computes `lines_sold` per product and `returns` per product as two small
aggregates and joins those (10,000 rows x 10,000 rows) instead of a
multi-million-row intermediate. Also avoids the row-multiplication risk of
joining a fact table to another fact table at different grain.

**Compute shared values once, not per row.** D13 used correlated subqueries in
`HAVING`, so the category average price and margin were recomputed for each of
10,000 products. Moving them into CTEs computes each category value once.

## 3. Slowest queries after optimization

| Query | Time | Why it's inherently heavy |
|---|---:|---|
| J2 market-basket pairs | ~7 s | Self-join of `FactSales` on `order_id` (~5M product pairs) |
| C11 cohort retention (recursive CTE) | ~4 s | Cohort x month-offset spine joined to all activity |
| B11 margin quartiles | ~3 s | Window function over a full product aggregate |

J2 is the kind of query that in production would be precomputed nightly into a
summary table rather than run on demand.

## 4. Caveat: results on this dataset are not business findings

The queries correctly answer the project's named questions (worst warehouse,
slowest country, highest-margin products, return hotspots, monthly retention),
but the *data* is synthetic with randomly drawn delays and margins. For
example, the "worst" warehouse averages 2.67 days delay against a network
average of ~2.4 — a spread that random noise alone produces. Treat the SQL as
the deliverable and the numbers as placeholders; don't cite them as insights.
Run the same queries on real data to get real answers.

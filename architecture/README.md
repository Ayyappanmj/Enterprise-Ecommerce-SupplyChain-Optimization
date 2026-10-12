# Phase 9 — Architecture Diagrams

Five diagrams, each as both `.mmd` (Mermaid source, editable) and rendered
`.svg` / `.png`. All were actually rendered and visually inspected here
(via `mermaid-cli`/`mmdc`) — unlike Phases 3/6/8, this phase needed no
external service or credentials, so there's no "untested" caveat on the
diagrams themselves. Two of the diagrams *depict* things that are untested
(the real GCS/S3/MySQL paths) — that's marked with color/dashed borders on
the diagram, not a limitation of the diagram.

| File | Shows |
|---|---|
| `etl_flow` | Phase 2's 3-source ETL pipeline: extract (incremental, retry-wrapped) → validate → quarantine/transform → load → watermark state |
| `cloud_architecture` | Phase 3's upload architecture: one interface, three providers (dry_run/GCS/S3), same bucket layout. Green solid = tested; red dashed = written but not run against a live account |
| `warehouse_star_schema` | Phase 6's full ER diagram: 5 dimensions + 3 facts, every column, every FK |
| `dashboard_flow` | Phase 8's path from warehouse → Power BI data model → DAX → 6 pages → interactivity, plus the two Phase 5 CSVs some measures need |
| `git_workflow` | A feature-branch-per-phase workflow, tagged at each merge, matching the phase structure of this actual repo |

## Regenerating

Requires `@mermaid-js/mermaid-cli` (`npm install -g @mermaid-js/mermaid-cli`)
and a Chromium/Chrome binary reachable by Puppeteer:

```bash
export PUPPETEER_EXECUTABLE_PATH=/path/to/chrome
echo '{"args": ["--no-sandbox"]}' > /tmp/pcfg.json
mmdc -i architecture/etl_flow.mmd -o architecture/etl_flow.svg -b white -p /tmp/pcfg.json --scale 2
mmdc -i architecture/etl_flow.mmd -o architecture/etl_flow.png -b white -p /tmp/pcfg.json --scale 2
# repeat for the other 4 .mmd files
```

Edit the `.mmd` source and re-run the two commands to update a diagram.

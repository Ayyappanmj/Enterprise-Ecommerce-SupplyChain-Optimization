# LinkedIn Post

## The post

---

A question I kept hearing in different e-commerce roles: **"are we losing
margin to shipping delays, or to returns?"** — and nobody ever had one
dataset that could actually answer it.

So I built the pipeline that would: a synthetic (but realistic) 500K-order
global e-commerce dataset, and everything needed to turn it into an answer.

**What's in it:**
🔹 Multi-source ETL — a mock Flask API with injected failures, retry logic,
incremental watermark loading, and quarantine for bad rows (not just a
happy-path script)
🔹 Cloud storage layer — GCS/S3/local, one interface, swap providers with an
env var
🔹 Cleaning + feature engineering — margin, CLV, return rate, warehouse
utilization, all in vectorized pandas
🔹 A Kimball star-schema warehouse (5 dims, 3 facts) and 120+ SQL queries —
window functions, recursive CTEs, the works
🔹 A Power BI data model + DAX, architecture diagrams, and a documented
8%-assumed-opex net margin formula that's consistent from the Python layer
all the way to the dashboard

**The part I actually want to talk about**: building this surfaced several
real bugs, and I think *how a project handles its own mistakes* says more
than a clean final README ever could.

→ A pandas dtype-contamination edge case caused a silent `ZeroDivisionError`
risk in margin calculations — caught by a deliberately adversarial unit
test, not by luck
→ A warehouse-capacity bug in the data generator was producing >2,000%
utilization numbers until I traced it back to the source
→ A missing foreign key meant a "return rate by country" metric would've
silently shown the same number for every country
→ Four SQL queries that ran fine on a sample but took 8+ seconds at 1.5M
rows — profiled and fixed before they became a slow dashboard

71 tests, 98.7% coverage, zero fabricated results. Every number in the repo
comes from actually running the code against real infrastructure where I
had it (SQLite, a live mock API, real `mermaid-cli` renders) — and where I
*didn't* have it (no MySQL server, no cloud credentials, no Power BI
Desktop in this environment), the README says so explicitly instead of
pretending.

It's a portfolio project on synthetic data, not a claimed production
deployment — and I think that's worth saying plainly rather than letting a
polished post imply otherwise.

Repo (full build log, every bug, every caveat): [link]

#DataEngineering #SQL #Python #PowerBI #ETL #DataAnalytics
#BusinessIntelligence #OpenToWork #PortfolioProject

---

## Why this post is written the way it is

No invented "$2M saved" or ""reduced delays by 40%"" headline number. This
project never ran against a real business, so a claim like that would be
fabricated — the kind of thing that looks great for one scroll and falls
apart in the first interview question about it ("walk me through how you
measured that"). Everything quantified above (71 tests, 98.7% coverage,
120+ queries, the specific bugs) is something a reader could open the repo
and verify in five minutes.

If you want a punchier, shorter variant for a platform with a tighter
character count, cut the bug list to 2 items and the explanation section
entirely — but keep the "synthetic data / portfolio project" line. It costs
little and is the difference between confident and misleading.

## Posting checklist

- [ ] Replace `[link]` with the actual repo URL
- [ ] Attach `linkedin/project_thumbnail.png` (or let LinkedIn auto-pull the
      GitHub social preview once that's set per `GITHUB_SETUP.md`)
- [ ] Tag any former colleagues/mentors who'd genuinely find this relevant —
      don't mass-tag for reach, it reads as spam and invites exactly the
      wrong kind of attention to an unverified-infra project
- [ ] Post Tuesday–Thursday, late morning in your audience's timezone
      (general LinkedIn engagement pattern, not specific to this project)

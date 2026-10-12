"""
Summarizes .cover files produced by Python's stdlib `trace` module into a
per-module coverage report. This exists because `coverage`/`pytest-cov`
could not be installed in the build environment (no network access) - see
README Phase 10. The numbers are real (computed from actual line-execution
data), just produced with a different, dependency-free tool than the
industry-standard `coverage.py`.

Usage:
    python -m trace --count --missing --coverdir=/tmp/covdir \\
        --module unittest discover -s tests
    python tests/summarize_trace_coverage.py /tmp/covdir
"""
import os
import re
import sys

_EXECUTED_LINE = re.compile(r"^\s*\d+:")

# Only these modules count as "our code" for the report - trace.py also
# produces .cover files for every stdlib/numpy/pandas module exercised along
# the way, which aren't relevant here.
PROJECT_MODULES = [
    "src.cleaning.cleaning_utils",
    "src.etl.load",
    "src.etl.transform",
    "src.etl.validators",
    "src.etl.state_manager",
    "src.utils.retry",
    "src.feature_engineering.order_features",
    "src.feature_engineering.customer_features",
    "src.warehouse.schema_builder",
    "src.warehouse.sqlite_loader",
]


def summarize(coverdir: str):
    rows = []
    for module in PROJECT_MODULES:
        path = os.path.join(coverdir, f"{module}.cover")
        if not os.path.exists(path):
            rows.append((module, 0, 0, 0.0))
            continue
        executed = missed = 0
        with open(path) as f:
            for line in f:
                if line.startswith(">>>>>>"):
                    missed += 1
                elif _EXECUTED_LINE.match(line):
                    executed += 1
        total = executed + missed
        pct = round(100 * executed / total, 1) if total else 0.0
        rows.append((module, executed, missed, pct))
    return rows


def main():
    coverdir = sys.argv[1] if len(sys.argv) > 1 else "/tmp/covdir"
    rows = summarize(coverdir)

    total_exec = sum(r[1] for r in rows)
    total_missed = sum(r[2] for r in rows)
    overall_pct = round(100 * total_exec / (total_exec + total_missed), 1) if (total_exec + total_missed) else 0.0

    print(f"{'Module':<45}{'Executed':>10}{'Missed':>10}{'Coverage':>10}")
    print("-" * 75)
    for module, executed, missed, pct in rows:
        print(f"{module:<45}{executed:>10}{missed:>10}{pct:>9}%")
    print("-" * 75)
    print(f"{'TOTAL':<45}{total_exec:>10}{total_missed:>10}{overall_pct:>9}%")


if __name__ == "__main__":
    main()

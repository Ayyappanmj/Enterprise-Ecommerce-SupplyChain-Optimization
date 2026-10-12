# GitHub Repository Setup

## Creating the repo

```bash
cd Enterprise-Ecommerce-SupplyChain-Optimization
gh repo create your-username/enterprise-ecommerce-supply-chain-optimization \
    --public --source=. --description "See description below" --push
```

Or via the UI: create an empty repo on GitHub (no README/license/gitignore —
this project already has all three), then:

```bash
git remote add origin git@github.com:your-username/enterprise-ecommerce-supply-chain-optimization.git
git push -u origin main --tags
```

## Suggested description

> End-to-end data engineering & BI portfolio project: synthetic global
> e-commerce dataset, multi-source ETL, cloud storage, star-schema warehouse,
> 120+ SQL analyses, Power BI dashboard design, and a tested pipeline —
> investigating margin compression from shipping delays and returns.

## Suggested topics

Set these via the GitHub UI (gear icon next to "About") or:
```bash
gh repo edit --add-topic data-engineering,etl,sql,python,pandas,mysql,power-bi,data-warehouse,star-schema,portfolio-project,data-analytics,business-intelligence
```

`data-engineering` · `etl` · `sql` · `python` · `pandas` · `mysql` ·
`power-bi` · `data-warehouse` · `star-schema` · `portfolio-project` ·
`data-analytics` · `business-intelligence`

## About the commit history

Run `git log --oneline` and you'll see one commit per phase, each with a
real diff matching that phase's content, tagged `v0.1.0` through `v0.12.0`
(plus one untagged initial-setup commit before `v0.1.0`).

**Be aware of what this is and isn't**: every commit's timestamp is from the
single session this project was assembled in — this is a real, logical
commit history (each commit genuinely corresponds to that phase's actual
work), not a fabricated multi-week development timeline. If you want commit
dates spread across however long you actually spend extending this project
going forward, that happens naturally as you make new commits from here.

**The commit author is a placeholder** (`Your Name <you@example.com>`).
Before pushing, either reconfigure git and amend, or rewrite history to
attach your own identity:

```bash
git config user.name "Your Actual Name"
git config user.email "you@example.com"

# rewrite every commit's author to your current git config:
git filter-branch -f --env-filter '
    export GIT_AUTHOR_NAME="$(git config user.name)"
    export GIT_AUTHOR_EMAIL="$(git config user.email)"
    export GIT_COMMITTER_NAME="$(git config user.name)"
    export GIT_COMMITTER_EMAIL="$(git config user.email)"
' --tag-name-filter cat -- --branches --tags
```

(`filter-branch` rewrites commit hashes; if you've already pushed, you'll
need `git push --force` afterward.)

## Release notes

See [RELEASE_NOTES.md](RELEASE_NOTES.md) — one entry per tag, describing what
that phase actually added. To publish them as GitHub Releases:

```bash
gh release create v0.11.0 --title "v0.11.0 - Documentation" \
    --notes-file <(sed -n '/## v0.11.0/,/## v0.10.0/p' RELEASE_NOTES.md)
# repeat per tag, or paste each section manually via the GitHub UI
```

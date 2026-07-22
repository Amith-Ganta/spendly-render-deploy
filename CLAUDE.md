# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

Spendly is a lightweight personal expense tracker built with Flask and SQLite.

---

## Architecture
```
spendly/
├── app.py              # All routes — single file, no blueprints
├── database/
│   ├── db.py           # SQLite schema + connection helpers: get_db(), init_db(), seed_db()
│   └── queries.py      # Read-side query helpers (profile data, stats, breakdowns)
├── templates/
│   ├── base.html       # Shared layout — all templates must extend this
│   └── *.html          # One template per page
├── static/
│   ├── css/
│   │   ├── style.css       # Global styles
│   │   └── landing.css     # Landing-page-only styles
│   └── js/
│       └── main.js         # Vanilla JS only
└── requirements.txt
```

**Where things belong:**
- New routes → `app.py` only, no blueprints
- DB logic → `database/` package only, never inline in routes
  - Schema, connection helpers, and writes (`get_db`, `init_db`, `seed_db`, `create_user`) → `database/db.py`
  - Read-side query helpers used by routes → `database/queries.py`
- New pages → new `.html` file extending `base.html`
- Page-specific styles → new `.css` file, not inline `<style>` tags

---

## Code style

- Python: PEP 8, snake_case for all variables and functions
- Templates: Jinja2 with `url_for()` for every internal link — never hardcode URLs
- Route functions: one responsibility only — fetch data, render template, done
- DB queries: always use parameterized queries (`?` placeholders) — never f-strings in SQL
- Error handling: use `abort()` for HTTP errors, not bare `return "error string"`

---

## Tech constraints

- **Flask only** — no FastAPI, no Django, no other web frameworks
- **SQLite only** — no PostgreSQL, no SQLAlchemy ORM, no external DB
- **Vanilla JS only** — no React, no jQuery, no npm packages
- **No new pip packages** — work within `requirements.txt` as-is unless explicitly told otherwise
- Python 3.10+ assumed — f-strings and `match` statements are fine

---

## Subagent Policy
- Always use a builtin explore subagent for codebase exploration 
  before implementing any new feature
- Always use a subagent to verify test results 
  after any implementation
- When asked to plan, delegate codebase research 
  to a subagent before presenting the plan
- always use a builtin plan subagent in plan mode

---

## Commands
```bash
# Setup
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Run dev server (port 5001)
python app.py

# Run all tests
pytest

# Run a specific test file
pytest tests/test_foo.py

# Run a specific test by name
pytest -k "test_name"

# Run tests with output visible
pytest -s

# Ship feature (finalize & merge)
git branch --show-current         # Identify current branch
git push -u origin BRANCH_NAME    # Push to feature branch
git switch main                   # Switch to main
git pull                          # Pull latest changes
git branch -D BRANCH_NAME         # Delete local branch
```

**Note:** Full ship workflow includes PR creation/merge via GitHub MCP (squash merge, then delete remote branch). See `.claude/commands/ship-feature.md` in repo for complete process.

---

## Implemented vs stub routes

| Route | Status |
|---|---|
| `GET /` | Implemented — renders `landing.html` |
| `GET /terms` | Implemented — renders `terms.html` |
| `GET /privacy` | Implemented — renders `privacy.html` |
| `GET /register` | Implemented — renders `register.html` |
| `GET /login` | Implemented — renders `login.html` |
| `POST /logout` | Implemented — clears session, redirects to landing |
| `GET /profile` | Implemented — renders `profile.html` (hardcoded data, Step 4) |
| `GET /expenses/add` | Implemented — renders `add_expense.html`, Step 7 |
| `GET /expenses/<id>/edit` | Implemented — renders `edit_expense.html`, Step 8 |
| `GET /expenses/<id>/delete` | Stub — Step 9 |

**Do not implement a stub route unless the active task explicitly targets that step.**

---

## Warnings and things to avoid

- **Never use raw string returns for stub routes** once a step is implemented — always render a template
- **Never hardcode URLs** in templates — always use `url_for()`
- **Never put DB logic in route functions** — it belongs in `database/db.py` (writes/schema) or `database/queries.py` (reads)
- **Never install new packages** mid-feature without flagging it — keep `requirements.txt` in sync
- **Never use JS frameworks** — the frontend is intentionally vanilla
- **`database/db.py` has `get_db()`, `init_db()`, `seed_db()`, `get_user_by_email()`, `create_user()` implemented**, and **`database/queries.py` has `get_user_by_id()`, `get_summary_stats()`, `get_recent_transactions()`, `get_category_breakdown()`** — use these helpers in routes, never inline DB logic
- **FK enforcement is manual** — SQLite foreign keys are off by default; `get_db()` must run `PRAGMA foreign_keys = ON` on every connection
- The app runs on **port 5001**, not the Flask default 5000 — don't change this

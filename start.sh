#!/usr/bin/env bash
# Render start script.
#
# app.py creates the SQLite schema and seed data inside its
# `if __name__ == "__main__":` block. Gunicorn imports app.py as a
# module, so that block never runs. Without it the tables do not exist
# and the first DB query 500s. To fix that without touching app logic,
# we call the existing (idempotent) init_db()/seed_db() functions once
# at boot, then hand off to gunicorn.
set -e

python -c "from database.db import init_db, seed_db; init_db(); seed_db()"

exec gunicorn app:app \
  --bind "0.0.0.0:${PORT:-5001}" \
  --workers 2 \
  --timeout 60 \
  --access-logfile - \
  --error-logfile -

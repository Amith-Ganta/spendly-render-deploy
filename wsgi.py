"""WSGI entry point for production servers (gunicorn).

app.py creates the SQLite schema and seed data inside its
``if __name__ == "__main__":`` block, which only runs with
``python app.py``. Gunicorn imports the module instead, so that block
never executes and the first DB query fails with "no such table".

Importing through this module runs the existing, idempotent
init_db()/seed_db() once at import time, before any request is served,
without modifying app.py or the database layer. Point the server at
``wsgi:app``.
"""
from database.db import init_db, seed_db

init_db()
seed_db()

from app import app  # noqa: E402  (import after DB init is intentional)

if __name__ == "__main__":
    import os

    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port)

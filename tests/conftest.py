import pytest


@pytest.fixture
def db_path(tmp_path):
    return str(tmp_path / "test.db")


@pytest.fixture
def app(db_path, monkeypatch):
    monkeypatch.setattr("database.db.DB_PATH", db_path)
    from app import app as flask_app
    from database.db import init_db, seed_db

    init_db()
    seed_db()
    flask_app.config["TESTING"] = True
    return flask_app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def seed_user_id(app):
    from database.db import get_db

    conn = get_db()
    try:
        row = conn.execute(
            "SELECT id FROM users WHERE email = ?", ("demo@spendly.com",)
        ).fetchone()
        return row["id"] if row else None
    finally:
        conn.close()


@pytest.fixture
def empty_user_id(app):
    from database.db import create_user

    return create_user("Empty Person", "empty@spendly.com", "secret123")


@pytest.fixture
def auth_client(client):
    client.post(
        "/login",
        data={"email": "demo@spendly.com", "password": "demo123"},
        follow_redirects=False,
    )
    return client

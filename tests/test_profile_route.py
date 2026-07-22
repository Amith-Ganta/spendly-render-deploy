RUPEE = "₹".encode("utf-8")


def test_profile_redirects_when_not_logged_in(client):
    response = client.get("/profile")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


def test_profile_renders_seed_user(auth_client):
    response = auth_client.get("/profile")
    assert response.status_code == 200
    body = response.data
    assert b"Demo User" in body
    assert b"demo@spendly.com" in body
    assert RUPEE in body
    assert b"296.25" in body
    assert b"Bills" in body


def test_profile_renders_empty_state_for_fresh_user(client, app):
    from database.db import create_user

    create_user("Fresh User", "fresh@spendly.com", "secret123")
    client.post(
        "/login",
        data={"email": "fresh@spendly.com", "password": "secret123"},
    )

    response = client.get("/profile")
    assert response.status_code == 200
    body = response.data
    assert b"Fresh User" in body
    assert RUPEE + b"0.00" in body
    assert "—".encode("utf-8") in body


def test_profile_redirects_when_user_deleted(auth_client, app, seed_user_id):
    from database.db import get_db

    conn = get_db()
    try:
        conn.execute("DELETE FROM expenses WHERE user_id = ?", (seed_user_id,))
        conn.execute("DELETE FROM users WHERE id = ?", (seed_user_id,))
        conn.commit()
    finally:
        conn.close()

    response = auth_client.get("/profile")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")

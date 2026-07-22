"""Test DELETE /expenses/<id>/delete — permanent expense deletion.

Spec: .claude/specs/09-delete-expense.md
"""

import pytest
from database.db import get_db


# ================================================================== #
# Module-level helpers                                              #
# ================================================================== #

def _get_seeded_expense(app):
    """Get the first seeded expense (user_id=1, amount=50.00)."""
    with app.app_context():
        conn = get_db()
        try:
            row = conn.execute(
                "SELECT id, user_id, amount, category, date, description FROM expenses "
                "WHERE user_id = 1 ORDER BY id LIMIT 1"
            ).fetchone()
        finally:
            conn.close()
    return dict(row) if row else None


def _expense_exists(expense_id):
    """Return True if the expense row exists in the DB."""
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT 1 FROM expenses WHERE id = ?",
            (expense_id,)
        ).fetchone()
    finally:
        conn.close()
    return row is not None


# ================================================================== #
# TestAuthGate                                                       #
# ================================================================== #

class TestAuthGate:
    """POST /expenses/<id>/delete while logged out must redirect to /login."""

    def test_redirects_to_login(self, client, app):
        """Unauthenticated POST must redirect (302) to /login."""
        expense = _get_seeded_expense(app)
        if not expense:
            pytest.skip("No seeded expense available")
        response = client.post(f"/expenses/{expense['id']}/delete")
        assert response.status_code == 302, (
            "Unauthenticated POST /expenses/<id>/delete must redirect (302)"
        )
        assert response.headers["Location"].endswith("/login"), (
            "Redirect must target /login"
        )

    def test_expense_unchanged(self, client, app):
        """Unauthenticated POST must not remove the row from the database."""
        expense = _get_seeded_expense(app)
        if not expense:
            pytest.skip("No seeded expense available")
        client.post(f"/expenses/{expense['id']}/delete")
        assert _expense_exists(expense["id"]), (
            "Expense row must not be deleted when POST is unauthenticated"
        )


# ================================================================== #
# TestDeleteSuccess                                                  #
# ================================================================== #

class TestDeleteSuccess:
    """POST /expenses/<id>/delete for own expense removes it and redirects."""

    def test_redirects_to_profile(self, auth_client, app):
        """Successful POST must redirect (302) to /profile."""
        expense = _get_seeded_expense(app)
        if not expense:
            pytest.skip("No seeded expense available")
        response = auth_client.post(f"/expenses/{expense['id']}/delete")
        assert response.status_code == 302, (
            "Expected 302 redirect after valid POST /expenses/<id>/delete"
        )
        assert response.headers["Location"].endswith("/profile"), (
            "Redirect must target /profile"
        )

    def test_expense_deleted(self, auth_client, app):
        """Successful POST must remove the row from the database."""
        expense = _get_seeded_expense(app)
        if not expense:
            pytest.skip("No seeded expense available")
        auth_client.post(f"/expenses/{expense['id']}/delete")
        assert not _expense_exists(expense["id"]), (
            "Expense row must be deleted from the database"
        )

    def test_flash_message(self, auth_client, app):
        """After successful POST, redirected profile must show 'Expense deleted.'."""
        expense = _get_seeded_expense(app)
        if not expense:
            pytest.skip("No seeded expense available")
        response = auth_client.post(
            f"/expenses/{expense['id']}/delete",
            follow_redirects=True
        )
        assert response.status_code == 200, "Profile page after redirect must return 200"
        assert b"Expense deleted." in response.data, (
            "Flash message 'Expense deleted.' must appear on the redirected profile page"
        )


# ================================================================== #
# TestOwnership                                                      #
# ================================================================== #

class TestOwnership:
    """Attempting to delete another user's expense must return 404."""

    def test_404_for_other_users_expense(self, auth_client, app, empty_user_id):
        """POST for another user's expense must return 404."""
        # Create an expense for empty_user_id
        conn = get_db()
        try:
            conn.execute(
                "INSERT INTO expenses (user_id, amount, category, date, description) "
                "VALUES (?, ?, ?, ?, ?)",
                (empty_user_id, 99.99, "Food", "2026-05-20", "Other user's expense"),
            )
            conn.commit()
            other_expense_id = conn.execute(
                "SELECT last_insert_rowid()"
            ).fetchone()[0]
        finally:
            conn.close()

        # auth_client is logged in as user_id=1, trying to delete empty_user_id's expense
        response = auth_client.post(f"/expenses/{other_expense_id}/delete")
        assert response.status_code == 404, (
            "POST to delete another user's expense must return 404"
        )
        assert _expense_exists(other_expense_id), (
            "Other user's expense must still exist after failed deletion attempt"
        )

    def test_404_for_nonexistent_expense(self, auth_client):
        """POST for a non-existent expense must return 404."""
        response = auth_client.post("/expenses/999999/delete")
        assert response.status_code == 404, (
            "POST to delete non-existent expense must return 404"
        )


# ================================================================== #
# TestMethodNotAllowed                                               #
# ================================================================== #

class TestMethodNotAllowed:
    """GET /expenses/<id>/delete must return 405 (Method Not Allowed)."""

    def test_get_not_allowed(self, auth_client, app):
        """GET to the route must return 405."""
        expense = _get_seeded_expense(app)
        if not expense:
            pytest.skip("No seeded expense available")
        response = auth_client.get(f"/expenses/{expense['id']}/delete")
        assert response.status_code == 405, (
            "GET /expenses/<id>/delete must return 405 (Method Not Allowed)"
        )

    def test_get_not_allowed_unauthenticated(self, client, app):
        """Unauthenticated GET must also return 405, not 302."""
        expense = _get_seeded_expense(app)
        if not expense:
            pytest.skip("No seeded expense available")
        response = client.get(f"/expenses/{expense['id']}/delete")
        assert response.status_code == 405, (
            "GET /expenses/<id>/delete must return 405 even when unauthenticated"
        )


# ================================================================== #
# TestProfileIntegration                                             #
# ================================================================== #

class TestProfileIntegration:
    """After deletion, the expense must not appear on the profile page."""

    def test_deleted_expense_absent_from_profile(self, auth_client, app):
        """After DELETE, the deleted expense must not appear in /profile response."""
        expense = _get_seeded_expense(app)
        if not expense:
            pytest.skip("No seeded expense available")

        # Get the description to search for in the profile page
        original_description = expense["description"]

        # Delete the expense
        auth_client.post(f"/expenses/{expense['id']}/delete")

        # Fetch the profile page and verify the deleted expense is absent
        response = auth_client.get("/profile")
        assert response.status_code == 200, "Profile page must return 200"

        # If the expense had a description, it should not appear in the response
        if original_description:
            assert original_description.encode() not in response.data, (
                "Deleted expense's description must not appear on /profile"
            )

"""
tests/test_07-add-expense.py

Spec-grounded tests for the Add Expense feature (Step 7).
Source of truth: .claude/specs/07-add-expense.md

All test logic is derived from what the spec says the feature SHOULD do.
Implementation files were consulted only for fixture names, route URLs,
and existing helper signatures — never to copy implementation behaviour.
"""

from datetime import date

import pytest


# ------------------------------------------------------------------ #
# DB query helpers (mirror pattern from tests/test_profile_route.py) #
# ------------------------------------------------------------------ #

def _count_expenses(user_id):
    """Return the total number of expense rows owned by user_id."""
    from database.db import get_db

    conn = get_db()
    try:
        return conn.execute(
            "SELECT COUNT(*) AS n FROM expenses WHERE user_id = ?",
            (user_id,),
        ).fetchone()["n"]
    finally:
        conn.close()


def _latest_expense(user_id):
    """Return the most recently inserted expense row for user_id, or None."""
    from database.db import get_db

    conn = get_db()
    try:
        return conn.execute(
            "SELECT * FROM expenses WHERE user_id = ? ORDER BY id DESC LIMIT 1",
            (user_id,),
        ).fetchone()
    finally:
        conn.close()


# ------------------------------------------------------------------ #
# Shared valid payload                                                #
# ------------------------------------------------------------------ #

VALID = {
    "amount": "42.50",
    "category": "Food",
    "date": "2026-05-12",
    "description": "Lunch",
}

CATEGORIES = (
    "Food", "Transport", "Bills", "Health",
    "Entertainment", "Shopping", "Other",
)


# ------------------------------------------------------------------ #
# TestAuthGate                                                        #
# ------------------------------------------------------------------ #

class TestAuthGate:
    """Both GET and POST /expenses/add must reject unauthenticated requests."""

    def test_get_redirects_anonymous_to_login(self, client):
        """Anonymous GET → 302 to /login."""
        response = client.get("/expenses/add")
        assert response.status_code == 302, (
            "Expected 302 redirect for unauthenticated GET /expenses/add"
        )
        assert response.headers["Location"].endswith("/login"), (
            "Redirect target should be /login"
        )

    def test_post_redirects_anonymous_to_login(self, client):
        """Anonymous POST → 302 to /login (not 200, not 400)."""
        response = client.post("/expenses/add", data=VALID)
        assert response.status_code == 302, (
            "Expected 302 redirect for unauthenticated POST /expenses/add"
        )
        assert response.headers["Location"].endswith("/login"), (
            "Redirect target should be /login"
        )

    def test_post_does_not_insert_when_anonymous(self, client, seed_user_id):
        """Anonymous POST must not write any expense row to the DB."""
        before = _count_expenses(seed_user_id)
        client.post("/expenses/add", data=VALID)
        assert _count_expenses(seed_user_id) == before, (
            "No expense row should be inserted for an unauthenticated POST"
        )


# ------------------------------------------------------------------ #
# TestGetForm                                                         #
# ------------------------------------------------------------------ #

class TestGetForm:
    """GET /expenses/add while logged in renders the add-expense form correctly."""

    def test_returns_200(self, auth_client):
        """Logged-in GET should return HTTP 200."""
        response = auth_client.get("/expenses/add")
        assert response.status_code == 200, "Expected 200 OK for authenticated GET"

    def test_today_date_prefilled(self, auth_client):
        """The date field must default to today's date in ISO format."""
        response = auth_client.get("/expenses/add")
        today_bytes = date.today().isoformat().encode()
        assert b'name="date"' in response.data, "Date input must have name='date'"
        assert today_bytes in response.data, (
            f"Today's date {date.today().isoformat()} must be pre-filled in the date field"
        )

    @pytest.mark.parametrize("category", CATEGORIES)
    def test_all_seven_categories_present(self, auth_client, category):
        """Each of the seven allowed categories must appear in the form dropdown."""
        response = auth_client.get("/expenses/add")
        assert category.encode() in response.data, (
            f"Category '{category}' is missing from the add-expense form"
        )

    def test_form_action_points_to_add_expense_route(self, auth_client):
        """Form action must resolve to /expenses/add (via url_for, never hardcoded)."""
        response = auth_client.get("/expenses/add")
        assert b'action="/expenses/add"' in response.data, (
            "Form action attribute must equal /expenses/add"
        )

    def test_template_extends_base_html_navbar(self, auth_client):
        """Page must extend base.html — confirmed by presence of navbar element."""
        response = auth_client.get("/expenses/add")
        assert b"navbar" in response.data, (
            "Response must contain navbar markup inherited from base.html"
        )

    def test_template_extends_base_html_brand(self, auth_client):
        """Page must extend base.html — confirmed by presence of Spendly brand name."""
        response = auth_client.get("/expenses/add")
        assert b"Spendly" in response.data, (
            "Response must contain Spendly brand name inherited from base.html"
        )

    def test_amount_input_present(self, auth_client):
        """Form must contain an amount input field."""
        response = auth_client.get("/expenses/add")
        assert b'name="amount"' in response.data, "Amount input must be present"

    def test_category_select_present(self, auth_client):
        """Form must contain a category select field."""
        response = auth_client.get("/expenses/add")
        assert b'name="category"' in response.data, "Category select must be present"

    def test_description_textarea_present(self, auth_client):
        """Form must contain an optional description textarea."""
        response = auth_client.get("/expenses/add")
        assert b'name="description"' in response.data, "Description textarea must be present"

    def test_rupee_symbol_on_form(self, auth_client):
        """Amount label must display the Indian Rupee symbol per project currency rule."""
        response = auth_client.get("/expenses/add")
        assert "₹".encode("utf-8") in response.data, (
            "Form must show the ₹ symbol on the amount field label"
        )


# ------------------------------------------------------------------ #
# TestValidPost                                                       #
# ------------------------------------------------------------------ #

class TestValidPost:
    """POST /expenses/add with valid data inserts one row and redirects to /profile."""

    def test_redirects_to_profile(self, auth_client):
        """Successful POST must redirect (302) to /profile."""
        response = auth_client.post("/expenses/add", data=VALID)
        assert response.status_code == 302, "Expected 302 redirect after valid POST"
        assert response.headers["Location"].endswith("/profile"), (
            "Redirect must target /profile"
        )

    def test_inserts_exactly_one_row(self, auth_client, seed_user_id):
        """Valid POST inserts exactly one new expense row for the logged-in user."""
        before = _count_expenses(seed_user_id)
        auth_client.post("/expenses/add", data=VALID)
        assert _count_expenses(seed_user_id) == before + 1, (
            "Exactly one expense row must be inserted after a valid POST"
        )

    def test_row_uses_session_user_id_not_form_field(self, auth_client, seed_user_id):
        """user_id on the new row must come from session, ignoring any form user_id field."""
        payload = dict(VALID)
        payload["user_id"] = "999999"  # stray form field — must be ignored
        auth_client.post("/expenses/add", data=payload)
        row = _latest_expense(seed_user_id)
        assert row is not None, "A row should have been inserted"
        assert row["user_id"] == seed_user_id, (
            "Row user_id must equal session user_id, not the stray form field value"
        )

    def test_row_stores_correct_amount(self, auth_client, seed_user_id):
        """Inserted row must store amount as a float equal to the submitted value."""
        auth_client.post("/expenses/add", data=VALID)
        row = _latest_expense(seed_user_id)
        assert row["amount"] == pytest.approx(42.50), (
            "Stored amount must equal the submitted value"
        )

    def test_row_stores_correct_category(self, auth_client, seed_user_id):
        """Inserted row must store the submitted category verbatim."""
        auth_client.post("/expenses/add", data=VALID)
        row = _latest_expense(seed_user_id)
        assert row["category"] == "Food", "Stored category must match submitted value"

    def test_row_stores_correct_date(self, auth_client, seed_user_id):
        """Inserted row must store the submitted date in ISO format."""
        auth_client.post("/expenses/add", data=VALID)
        row = _latest_expense(seed_user_id)
        assert row["date"] == "2026-05-12", "Stored date must match submitted value"

    def test_row_stores_description(self, auth_client, seed_user_id):
        """Non-blank description must be stored (trimmed) in the row."""
        auth_client.post("/expenses/add", data=VALID)
        row = _latest_expense(seed_user_id)
        assert row["description"] == "Lunch", (
            "Non-empty description must be stored verbatim (after trim)"
        )

    def test_success_flash_message(self, auth_client):
        """After a successful POST, following the redirect must show 'Expense added.'."""
        response = auth_client.post("/expenses/add", data=VALID, follow_redirects=True)
        assert response.status_code == 200, "Profile page after redirect must return 200"
        assert b"Expense added." in response.data, (
            "Flash message 'Expense added.' must appear on the redirected profile page"
        )

    def test_blank_description_stored_as_null(self, auth_client, seed_user_id):
        """Submitting an empty description must store NULL (not empty string) in the DB."""
        payload = dict(VALID, description="")
        auth_client.post("/expenses/add", data=payload)
        row = _latest_expense(seed_user_id)
        assert row is not None, "Row should have been inserted"
        assert row["description"] is None, (
            "Empty description must be stored as NULL, not as an empty string"
        )

    def test_whitespace_only_description_stored_as_null(self, auth_client, seed_user_id):
        """Whitespace-only description must be trimmed to NULL in the DB."""
        payload = dict(VALID, description="   \t  ")
        auth_client.post("/expenses/add", data=payload)
        row = _latest_expense(seed_user_id)
        assert row is not None, "Row should have been inserted"
        assert row["description"] is None, (
            "Whitespace-only description must be stored as NULL after trimming"
        )

    def test_injected_user_id_form_field_is_ignored(self, auth_client, seed_user_id,
                                                     empty_user_id):
        """Even if a different valid user_id is injected via form, session user_id wins."""
        payload = dict(VALID)
        payload["user_id"] = str(empty_user_id)
        auth_client.post("/expenses/add", data=payload)
        row = _latest_expense(seed_user_id)
        assert row is not None, "Row should have been inserted for the session user"
        assert row["user_id"] == seed_user_id, (
            "Injected user_id form field must be ignored; session user_id must be used"
        )
        # empty_user_id must gain no rows
        assert _count_expenses(empty_user_id) == 0, (
            "No row should be inserted for the injected user_id"
        )


# ------------------------------------------------------------------ #
# TestInvalidAmount                                                   #
# ------------------------------------------------------------------ #

class TestInvalidAmount:
    """Invalid amount values must re-render the form (200) with an error flash."""

    @pytest.mark.parametrize("bad_amount,label", [
        ("0",         "zero"),
        ("-5",        "negative"),
        ("-0.01",     "small negative"),
        ("abc",       "non-numeric string"),
        ("",          "empty string"),
        ("   ",       "whitespace only"),
        ("1e999",     "overflow float string"),
        ("20000000",  "over MAX_AMOUNT (10_000_000)"),
    ])
    def test_rerenders_form_no_insert(self, auth_client, seed_user_id, bad_amount, label):
        """Bad amount must not insert any row and must return 200."""
        before = _count_expenses(seed_user_id)
        response = auth_client.post(
            "/expenses/add", data=dict(VALID, amount=bad_amount)
        )
        assert response.status_code == 200, (
            f"Amount '{label}' must re-render form (200), got {response.status_code}"
        )
        assert _count_expenses(seed_user_id) == before, (
            f"Amount '{label}' must not insert a row"
        )

    def test_zero_amount_shows_flash_error(self, auth_client):
        """Zero amount must flash an error message."""
        response = auth_client.post("/expenses/add", data=dict(VALID, amount="0"))
        assert b"Amount must be a positive number." in response.data, (
            "Flash error for zero amount must be present"
        )

    def test_negative_amount_shows_flash_error(self, auth_client):
        """Negative amount must flash an error message."""
        response = auth_client.post("/expenses/add", data=dict(VALID, amount="-10"))
        assert b"Amount must be a positive number." in response.data, (
            "Flash error for negative amount must be present"
        )

    def test_non_numeric_amount_shows_flash_error(self, auth_client):
        """Non-numeric amount must flash an error message."""
        response = auth_client.post("/expenses/add", data=dict(VALID, amount="xyz"))
        assert b"Amount must be a positive number." in response.data, (
            "Flash error for non-numeric amount must be present"
        )

    def test_over_max_amount_shows_distinct_flash_error(self, auth_client):
        """An amount above MAX_AMOUNT must flash a 'must not exceed' error, NOT the generic positive-number message."""
        response = auth_client.post("/expenses/add", data=dict(VALID, amount="20000000"))
        assert b"must not exceed" in response.data, (
            "Flash error for too-large amount must indicate the value exceeds the cap"
        )
        # The generic 'positive number' message would be misleading here and must not be the one shown.
        assert b"Amount must be a positive number." not in response.data, (
            "Generic positive-number error must not be shown for an amount that is positive but too large"
        )

    def test_submitted_values_preserved_on_error(self, auth_client):
        """On amount error the submitted date must be re-populated in the re-rendered form."""
        response = auth_client.post(
            "/expenses/add",
            data=dict(VALID, amount="bad", date="2026-06-01"),
        )
        assert b"2026-06-01" in response.data, (
            "Previously submitted date must be preserved when re-rendering after amount error"
        )

    def test_submitted_category_preserved_on_error(self, auth_client):
        """On amount error the submitted category must be rendered as the selected option."""
        response = auth_client.post(
            "/expenses/add",
            data=dict(VALID, amount="bad", category="Transport"),
        )
        # The Transport option must carry the selected attribute, not merely appear in the page
        # (the word "Transport" appears unconditionally because it is one of the seven categories).
        assert b'value="Transport" selected' in response.data, (
            "Previously submitted category 'Transport' must be rendered as selected in the dropdown"
        )


# ------------------------------------------------------------------ #
# TestInvalidCategory                                                 #
# ------------------------------------------------------------------ #

class TestInvalidCategory:
    """Invalid or unknown categories must re-render the form (200) with an error flash."""

    @pytest.mark.parametrize("bad_category,label", [
        ("Bogus",        "unknown string"),
        ("",             "empty string"),
        ("food",         "lowercase valid name"),
        ("FOOD",         "uppercase valid name"),
        ("Food ",        "trailing space"),
        (" Food",        "leading space"),
        ("<script>",     "XSS attempt"),
        ("' OR '1'='1", "SQL injection attempt"),
    ])
    def test_rerenders_form_no_insert(self, auth_client, seed_user_id, bad_category, label):
        """Invalid category must not insert any row and must return 200."""
        before = _count_expenses(seed_user_id)
        response = auth_client.post(
            "/expenses/add", data=dict(VALID, category=bad_category)
        )
        assert response.status_code == 200, (
            f"Category '{label}' must re-render form (200)"
        )
        assert _count_expenses(seed_user_id) == before, (
            f"Category '{label}' must not insert a row"
        )

    def test_unknown_category_shows_flash_error(self, auth_client):
        """An unknown category name must produce a flash error message."""
        response = auth_client.post(
            "/expenses/add", data=dict(VALID, category="Bogus")
        )
        assert b"Please choose a valid category." in response.data, (
            "Flash error for unknown category must be present"
        )

    def test_empty_category_shows_flash_error(self, auth_client):
        """An empty category string must produce a flash error message."""
        response = auth_client.post(
            "/expenses/add", data=dict(VALID, category="")
        )
        assert b"Please choose a valid category." in response.data, (
            "Flash error for empty category must be present"
        )


# ------------------------------------------------------------------ #
# TestInvalidDate                                                     #
# ------------------------------------------------------------------ #

class TestInvalidDate:
    """Invalid or malformed dates must re-render the form (200) with an error flash."""

    @pytest.mark.parametrize("bad_date,label", [
        ("2026-13-99",  "impossible month+day"),
        ("2026-00-01",  "zero month"),
        ("99-99-9999",  "reversed format"),
        ("01/05/2026",  "slashed UK format"),
        ("05-01-2026",  "MM-DD-YYYY format"),
        ("not-a-date",  "arbitrary string"),
        ("",            "empty string"),
        ("   ",         "whitespace only"),
    ])
    def test_rerenders_form_no_insert(self, auth_client, seed_user_id, bad_date, label):
        """Invalid date must not insert any row and must return 200."""
        before = _count_expenses(seed_user_id)
        response = auth_client.post(
            "/expenses/add", data=dict(VALID, date=bad_date)
        )
        assert response.status_code == 200, (
            f"Date '{label}' must re-render form (200)"
        )
        assert _count_expenses(seed_user_id) == before, (
            f"Date '{label}' must not insert a row"
        )

    def test_malformed_date_shows_flash_error(self, auth_client):
        """A malformed date string must produce a flash error message."""
        response = auth_client.post(
            "/expenses/add", data=dict(VALID, date="2026-13-99")
        )
        assert b"Please enter a valid date." in response.data, (
            "Flash error for malformed date must be present"
        )

    def test_empty_date_shows_flash_error(self, auth_client):
        """An empty date must produce a flash error message."""
        response = auth_client.post(
            "/expenses/add", data=dict(VALID, date="")
        )
        assert b"Please enter a valid date." in response.data, (
            "Flash error for empty date must be present"
        )

    def test_submitted_amount_preserved_after_date_error(self, auth_client):
        """On date error the submitted amount must be re-populated in the re-rendered form."""
        response = auth_client.post(
            "/expenses/add",
            data=dict(VALID, date="bad-date", amount="123.45"),
        )
        assert b"123.45" in response.data, (
            "Previously submitted amount must be preserved when re-rendering after date error"
        )


# ------------------------------------------------------------------ #
# TestProfileIntegration                                              #
# ------------------------------------------------------------------ #

class TestProfileIntegration:
    """After a successful add-expense POST, the new expense must be visible on /profile."""

    def test_new_expense_appears_in_recent_transactions(self, auth_client):
        """The description submitted in add-expense must appear in profile's Recent Transactions."""
        payload = dict(VALID, description="My unique bookstore haul",
                       amount="77.77", date=date.today().isoformat())
        auth_client.post("/expenses/add", data=payload)
        response = auth_client.get("/profile")
        assert response.status_code == 200
        assert b"My unique bookstore haul" in response.data, (
            "New expense description must appear in the Recent Transactions section on /profile"
        )

    def test_new_expense_amount_appears_on_profile(self, auth_client):
        """The amount submitted in add-expense must appear on /profile after redirect."""
        payload = dict(VALID, amount="88.88", date=date.today().isoformat())
        auth_client.post("/expenses/add", data=payload)
        response = auth_client.get("/profile")
        assert b"88.88" in response.data, (
            "New expense amount must be visible on /profile after successful add"
        )

    def test_transaction_count_increments_on_profile(self, auth_client, seed_user_id):
        """Adding a valid expense must increment the underlying transaction count by exactly 1."""
        before = _count_expenses(seed_user_id)
        post_response = auth_client.post("/expenses/add", data=VALID)
        assert post_response.status_code == 302, (
            "Valid POST must redirect (302) — otherwise the count assertion below is meaningless"
        )

        after = _count_expenses(seed_user_id)
        assert after == before + 1, (
            f"Expense count must increase by exactly 1; was {before}, became {after}"
        )

        # And the profile page must still render successfully after the new row exists.
        profile_response = auth_client.get("/profile")
        assert profile_response.status_code == 200, (
            "Profile must return 200 after adding an expense"
        )

    def test_add_expense_cta_present_on_profile(self, auth_client):
        """The '+ Add Expense' CTA on the profile page must link to /expenses/add."""
        response = auth_client.get("/profile")
        assert response.status_code == 200
        assert b"/expenses/add" in response.data, (
            "Profile page must contain a link to /expenses/add for the Add Expense CTA"
        )

    def test_add_expense_navbar_link_present_when_logged_in(self, auth_client):
        """When logged in, the navbar must contain a link to /expenses/add labelled 'Add Expense'."""
        response = auth_client.get("/profile")
        assert b'href="/expenses/add"' in response.data, (
            "Navbar must contain href='/expenses/add' when user is authenticated"
        )
        assert b"Add Expense" in response.data, (
            "Navbar must contain the text 'Add Expense' when user is authenticated"
        )

    def test_add_expense_navbar_link_absent_when_logged_out(self, client):
        """When logged out, the navbar must NOT expose the Add Expense link."""
        response = client.get("/")
        assert b'href="/expenses/add"' not in response.data, (
            "Navbar must not show /expenses/add link to unauthenticated visitors"
        )

    def test_add_expense_link_absent_on_login_page(self, client):
        """The login page (unauthenticated) must not contain the Add Expense navbar link."""
        response = client.get("/login")
        assert b'href="/expenses/add"' not in response.data, (
            "Login page must not show /expenses/add link"
        )

    def test_category_appears_in_profile_breakdown_after_add(self, auth_client):
        """After adding a Shopping expense, the Shopping category must appear in the breakdown."""
        payload = dict(VALID, category="Shopping", amount="50.00",
                       date=date.today().isoformat())
        auth_client.post("/expenses/add", data=payload)
        response = auth_client.get("/profile")
        assert b"Shopping" in response.data, (
            "Newly added category must appear in the Spending by Category breakdown on /profile"
        )

    def test_multiple_valid_posts_all_inserted(self, auth_client, seed_user_id):
        """Posting multiple valid expenses must each create a separate row."""
        before = _count_expenses(seed_user_id)
        for i in range(3):
            auth_client.post(
                "/expenses/add",
                data=dict(VALID, amount=str(10 + i), description=f"item {i}"),
            )
        assert _count_expenses(seed_user_id) == before + 3, (
            "Three sequential valid POSTs must insert three separate expense rows"
        )

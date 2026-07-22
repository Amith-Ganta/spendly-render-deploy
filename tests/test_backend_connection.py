import re

from database.queries import (
    get_category_breakdown,
    get_recent_transactions,
    get_summary_stats,
    get_user_by_id,
)


# ---------- get_user_by_id ----------

def test_get_user_by_id_returns_seed_user(app, seed_user_id):
    user = get_user_by_id(seed_user_id)
    assert user["name"] == "Demo User"
    assert user["email"] == "demo@spendly.com"
    assert user["initials"] == "DU"
    assert re.match(r"^[A-Z][a-z]+ \d{4}$", user["member_since"])


def test_get_user_by_id_missing(app):
    assert get_user_by_id(99999) is None


# ---------- get_summary_stats ----------

def test_get_summary_stats_seed(app, seed_user_id):
    stats = get_summary_stats(seed_user_id)
    assert stats["total_spent"] == "296.25"
    assert stats["transaction_count"] == 8
    assert stats["top_category"] == "Bills"


def test_get_summary_stats_empty(app, empty_user_id):
    assert get_summary_stats(empty_user_id) == {
        "total_spent": "0.00",
        "transaction_count": 0,
        "top_category": "—",
    }


# ---------- get_recent_transactions ----------

def test_get_recent_transactions_seed(app, seed_user_id):
    txs = get_recent_transactions(seed_user_id)
    assert len(txs) == 8
    for tx in txs:
        assert set(tx.keys()) == {"date", "description", "category", "amount"}
    assert txs[0]["date"] == "15 May 2026"
    assert txs[0]["description"] == "Miscellaneous"


def test_get_recent_transactions_empty(app, empty_user_id):
    assert get_recent_transactions(empty_user_id) == []


# ---------- get_category_breakdown ----------

def test_get_category_breakdown_seed(app, seed_user_id):
    cats = get_category_breakdown(seed_user_id)
    assert len(cats) == 7
    for cat in cats:
        assert set(cat.keys()) == {"name", "total", "pct"}
        assert isinstance(cat["pct"], int)
    totals = [float(c["total"]) for c in cats]
    assert totals == sorted(totals, reverse=True)
    assert sum(c["pct"] for c in cats) == 100
    assert cats[0]["name"] == "Bills"


def test_get_category_breakdown_empty(app, empty_user_id):
    assert get_category_breakdown(empty_user_id) == []


def test_get_category_breakdown_all_zero_amounts(app, empty_user_id):
    from database.db import get_db

    conn = get_db()
    try:
        conn.executemany(
            "INSERT INTO expenses (user_id, amount, category, date, description) "
            "VALUES (?, ?, ?, ?, ?)",
            [
                (empty_user_id, 0.0, "Food", "2026-05-01", "Free sample"),
                (empty_user_id, 0.0, "Transport", "2026-05-02", "Walked"),
            ],
        )
        conn.commit()
    finally:
        conn.close()

    cats = get_category_breakdown(empty_user_id)
    assert len(cats) == 2
    assert all(c["pct"] == 0 for c in cats)
    assert all(c["total"] == "0.00" for c in cats)

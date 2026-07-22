from database import queries


def test_summary_stats_no_filter_unchanged(seed_user_id):
    stats = queries.get_summary_stats(seed_user_id)
    assert stats == {
        "total_spent": "296.25",
        "transaction_count": 8,
        "top_category": "Bills",
    }


def test_summary_stats_filtered_window(seed_user_id):
    stats = queries.get_summary_stats(
        seed_user_id, date_from="2026-05-01", date_to="2026-05-07"
    )
    assert stats["transaction_count"] == 5
    assert stats["total_spent"] == "207.50"
    assert stats["top_category"] == "Bills"


def test_summary_stats_empty_window(seed_user_id):
    stats = queries.get_summary_stats(
        seed_user_id, date_from="2027-01-01", date_to="2027-01-31"
    )
    assert stats == {
        "total_spent": "0.00",
        "transaction_count": 0,
        "top_category": "—",
    }


def test_recent_transactions_filtered_window(seed_user_id):
    rows = queries.get_recent_transactions(
        seed_user_id, date_from="2026-05-01", date_to="2026-05-05"
    )
    assert len(rows) == 4
    dates = [r["date"] for r in rows]
    assert dates == ["5 May 2026", "3 May 2026", "2 May 2026", "1 May 2026"]


def test_recent_transactions_limit_with_filter(seed_user_id):
    rows = queries.get_recent_transactions(
        seed_user_id, limit=2, date_from="2026-05-01", date_to="2026-05-15"
    )
    assert len(rows) == 2
    assert rows[0]["date"] == "15 May 2026"
    assert rows[1]["date"] == "12 May 2026"


def test_category_breakdown_filtered_single_category(seed_user_id):
    rows = queries.get_category_breakdown(
        seed_user_id, date_from="2026-05-05", date_to="2026-05-05"
    )
    assert len(rows) == 1
    assert rows[0]["name"] == "Health"
    assert rows[0]["pct"] == 100


def test_category_breakdown_empty_window(seed_user_id):
    rows = queries.get_category_breakdown(
        seed_user_id, date_from="2027-01-01", date_to="2027-01-31"
    )
    assert rows == []


def test_date_from_alone(seed_user_id):
    stats = queries.get_summary_stats(seed_user_id, date_from="2026-05-10")
    assert stats["transaction_count"] == 3
    assert stats["total_spent"] == "88.75"


def test_date_to_alone(seed_user_id):
    stats = queries.get_summary_stats(seed_user_id, date_to="2026-05-05")
    assert stats["transaction_count"] == 4
    assert stats["total_spent"] == "192.50"


def test_other_user_unaffected(empty_user_id):
    stats = queries.get_summary_stats(
        empty_user_id, date_from="2026-05-01", date_to="2026-05-31"
    )
    assert stats["transaction_count"] == 0
    txs = queries.get_recent_transactions(
        empty_user_id, date_from="2026-05-01", date_to="2026-05-31"
    )
    assert txs == []

import pytest

from app import _preset_range


def test_no_params_renders_all_time_active(auth_client):
    response = auth_client.get("/profile")
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "filter-preset--active" in body
    # All Time link is the only one without query params on its href
    assert 'href="/profile"' in body


def test_this_month_params_marks_active(auth_client):
    df, dt = _preset_range("month")
    response = auth_client.get(f"/profile?date_from={df}&date_to={dt}")
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert body.count("filter-preset--active") == 1
    # The active class must appear on the This Month preset
    this_month_idx = body.find(">This Month<")
    active_idx = body.find("filter-preset--active")
    # active class appears within a reasonable distance before the link text
    assert 0 < active_idx < this_month_idx


def test_custom_range_marks_custom_active(auth_client):
    response = auth_client.get(
        "/profile?date_from=2026-05-03&date_to=2026-05-07"
    )
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "filter-bar__custom--active" in body
    assert "filter-preset--active" not in body


def test_filter_changes_displayed_total(auth_client):
    response = auth_client.get(
        "/profile?date_from=2026-05-01&date_to=2026-05-03"
    )
    body = response.get_data(as_text=True)
    assert "₹167.50" in body
    assert "₹296.25" not in body


@pytest.mark.parametrize(
    "param", ["not-a-date", "2026-13-40", "2026/05/01", "2026-02-30"]
)
def test_malformed_date_falls_back(auth_client, param):
    response = auth_client.get(f"/profile?date_from={param}")
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "Start date must be before end date." not in body
    assert "₹296.25" in body


def test_inverted_range_flashes_error(auth_client):
    response = auth_client.get(
        "/profile?date_from=2026-05-15&date_to=2026-05-01"
    )
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "Start date must be before end date." in body
    assert "₹296.25" in body


def test_empty_range_shows_zero_state(auth_client):
    response = auth_client.get(
        "/profile?date_from=2027-01-01&date_to=2027-01-31"
    )
    body = response.get_data(as_text=True)
    assert "₹0.00" in body
    assert "No transactions in this range." in body
    assert "No category data for this range." in body


def test_input_values_echoed(auth_client):
    response = auth_client.get(
        "/profile?date_from=2026-05-03&date_to=2026-05-07"
    )
    body = response.get_data(as_text=True)
    assert 'value="2026-05-03"' in body
    assert 'value="2026-05-07"' in body


def test_unauthenticated_redirects(client):
    response = client.get("/profile?date_from=2026-05-01")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]

import math
import os
import secrets
import sqlite3
from datetime import date, datetime
from flask import Flask, render_template, request, redirect, url_for, flash, abort, session
from werkzeug.security import check_password_hash
from database.db import init_db, seed_db, create_user, create_expense, get_user_by_email
from database import queries

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY") or secrets.token_hex(32)

EXPENSE_CATEGORIES = (
    "Food", "Transport", "Bills", "Health",
    "Entertainment", "Shopping", "Other",
)
MAX_AMOUNT = 10_000_000
MAX_DESCRIPTION_LENGTH = 200
MIN_EXPENSE_YEAR = 2000


# ------------------------------------------------------------------ #
# Helpers                                                             #
# ------------------------------------------------------------------ #

def login_required():
    if not session.get("user_id"):
        abort(401)


def _parse_iso_date(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def _preset_range(preset, today=None):
    today = today or date.today()
    if preset == "month":
        n = 1
    elif preset == "3months":
        n = 3
    elif preset == "6months":
        n = 6
    else:
        return (None, None)
    months_back = n - 1
    y, m = today.year, today.month - months_back
    while m <= 0:
        m += 12
        y -= 1
    return (date(y, m, 1).isoformat(), today.isoformat())


def _detect_active_preset(date_from_str, date_to_str, today=None):
    if not date_from_str and not date_to_str:
        return "all"
    for name in ("month", "3months", "6months"):
        if (date_from_str, date_to_str) == _preset_range(name, today):
            return name
    return "custom"


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    if session.get("user_id"):
        return redirect(url_for("profile"))
    return render_template("landing.html")


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if session.get("user_id"):
        return redirect(url_for("profile"))
    if request.method == "GET":
        return render_template("register.html")

    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    password = request.form.get("password", "")
    confirm_password = request.form.get("confirm_password", "")

    if not name or not email or not password or not confirm_password:
        flash("All fields are required.")
        return render_template("register.html")

    if password != confirm_password:
        flash("Passwords do not match.")
        return render_template("register.html")

    if len(password) < 8:
        flash("Password must be at least 8 characters.")
        return render_template("register.html")

    try:
        create_user(name, email, password)
    except sqlite3.IntegrityError:
        flash("Email already registered.")
        return render_template("register.html")

    flash("Account created! Please sign in.")
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("profile"))
    if request.method == "GET":
        return render_template("login.html")

    email = request.form.get("email", "").strip()
    password = request.form.get("password", "")

    user = get_user_by_email(email)
    if not user or not check_password_hash(user["password_hash"], password):
        return render_template("login.html", error="Invalid email or password.")

    session.clear()
    session["user_id"] = user["id"]
    return redirect(url_for("landing"))


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("landing"))


@app.route("/profile")
def profile():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))

    user = queries.get_user_by_id(user_id)
    if user is None:
        session.clear()
        return redirect(url_for("login"))

    df = _parse_iso_date(request.args.get("date_from", "").strip())
    dt = _parse_iso_date(request.args.get("date_to", "").strip())
    if df and dt and df > dt:
        flash("Start date must be before end date.")
        df = dt = None

    df_iso = df.isoformat() if df else None
    dt_iso = dt.isoformat() if dt else None

    stats = queries.get_summary_stats(user_id, date_from=df_iso, date_to=dt_iso)
    transactions = queries.get_recent_transactions(user_id, date_from=df_iso, date_to=dt_iso)
    categories = queries.get_category_breakdown(user_id, date_from=df_iso, date_to=dt_iso)

    today = date.today()
    presets = {
        "month": _preset_range("month", today),
        "3months": _preset_range("3months", today),
        "6months": _preset_range("6months", today),
    }
    return render_template(
        "profile.html",
        user=user,
        stats=stats,
        transactions=transactions,
        categories=categories,
        date_from=df_iso or "",
        date_to=dt_iso or "",
        presets=presets,
        active_preset=_detect_active_preset(df_iso, dt_iso, today),
    )


@app.route("/analytics")
def analytics():
    if not session.get("user_id"):
        return redirect(url_for("login"))
    return render_template("analytics.html")


@app.route("/expenses/add", methods=["GET", "POST"])
def add_expense():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    today = date.today().isoformat()
    if request.method == "GET":
        return _render_add_form({}, today)

    form = {
        "amount":      request.form.get("amount", ""),
        "category":    request.form.get("category", ""),
        "date":        request.form.get("date", ""),
        "description": request.form.get("description", ""),
    }

    try:
        amount = float(form["amount"])
        if not math.isfinite(amount) or amount <= 0:
            raise ValueError
    except (ValueError, TypeError):
        flash("Amount must be a positive number.")
        return _render_add_form(form, today)

    if amount > MAX_AMOUNT:
        flash(f"Amount must not exceed ₹{MAX_AMOUNT:,.2f}.")
        return _render_add_form(form, today)

    if form["category"] not in EXPENSE_CATEGORIES:
        flash("Please choose a valid category.")
        return _render_add_form(form, today)

    try:
        parsed_date = datetime.strptime(form["date"], "%Y-%m-%d").date()
        if parsed_date.year < MIN_EXPENSE_YEAR or parsed_date > date.today():
            raise ValueError
    except ValueError:
        flash("Please enter a valid date.")
        return _render_add_form(form, today)

    description = form["description"].strip()
    if len(description) > MAX_DESCRIPTION_LENGTH:
        flash(f"Description must be {MAX_DESCRIPTION_LENGTH} characters or fewer.")
        return _render_add_form(form, today)

    create_expense(
        session["user_id"], amount, form["category"],
        form["date"], description or None,
    )
    flash("Expense added.")
    return redirect(url_for("profile"))


def _render_add_form(form, today):
    return render_template(
        "add_expense.html",
        categories=EXPENSE_CATEGORIES,
        today=today,
        form=form,
    )


@app.route("/expenses/<int:id>/edit", methods=["GET", "POST"])
def edit_expense(id):
    if not session.get("user_id"):
        return redirect(url_for("login"))

    expense = queries.get_expense_by_id(id, session["user_id"])
    if expense is None:
        abort(404)

    today = date.today().isoformat()

    if request.method == "GET":
        form = {
            "amount":      str(expense["amount"]),
            "category":    expense["category"],
            "date":        expense["date"],
            "description": expense["description"] or "",
        }
        return render_template("edit_expense.html", expense=expense,
                               categories=EXPENSE_CATEGORIES, form=form, today=today)

    # POST — same validation chain as add_expense
    form = {
        "amount":      request.form.get("amount", ""),
        "category":    request.form.get("category", ""),
        "date":        request.form.get("date", ""),
        "description": request.form.get("description", ""),
    }

    def rerender(msg):
        flash(msg)
        return render_template("edit_expense.html", expense=expense,
                               categories=EXPENSE_CATEGORIES, form=form, today=today)

    try:
        amount = float(form["amount"])
        if not math.isfinite(amount) or amount <= 0:
            raise ValueError
    except (ValueError, TypeError):
        return rerender("Amount must be a positive number.")

    if amount > MAX_AMOUNT:
        return rerender(f"Amount must not exceed ₹{MAX_AMOUNT:,.2f}.")

    if form["category"] not in EXPENSE_CATEGORIES:
        return rerender("Please choose a valid category.")

    try:
        parsed_date = datetime.strptime(form["date"], "%Y-%m-%d").date()
        if parsed_date.year < MIN_EXPENSE_YEAR or parsed_date > date.today():
            raise ValueError
    except ValueError:
        return rerender("Please enter a valid date.")

    description = form["description"].strip()
    if len(description) > MAX_DESCRIPTION_LENGTH:
        return rerender(f"Description must be {MAX_DESCRIPTION_LENGTH} characters or fewer.")

    queries.update_expense(
        id, session["user_id"], amount,
        form["category"], form["date"], description or None,
    )
    flash("Expense updated.")
    return redirect(url_for("profile"))


@app.route("/expenses/<int:id>/delete", methods=["POST"])
def delete_expense(id):
    if not session.get("user_id"):
        return redirect(url_for("login"))

    expense = queries.get_expense_by_id(id, session["user_id"])
    if expense is None:
        abort(404)

    queries.delete_expense(id, session["user_id"])
    flash("Expense deleted.")
    return redirect(url_for("profile"))


if __name__ == "__main__":
    with app.app_context():
        init_db()
        seed_db()
    port = int(os.environ.get("PORT", 5001))
    debug = os.environ.get("FLASK_ENV") == "development"
    app.run(debug=debug, host="0.0.0.0", port=port)

from datetime import datetime, timezone, timedelta
import json
import logging

from flask import Blueprint, render_template, session, redirect, url_for, request, jsonify, flash
from sqlalchemy import func, extract

from models import db, User, Transaction, CategoryRule
from services.gmail_service import get_gmail_service, fetch_transaction_emails, get_message_details
from services.parser import parse_transaction_email
from services.categorizer import categorize, load_default_rules, get_category_data

logger = logging.getLogger(__name__)

main_bp = Blueprint("main", __name__)


def login_required(f):
    from functools import wraps

    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("main.home"))
        return f(*args, **kwargs)

    return decorated


@main_bp.route("/")
def home():
    if "user_id" in session:
        return redirect(url_for("main.dashboard"))
    return render_template("home.html")


@main_bp.route("/dashboard")
@login_required
def dashboard():
    user = User.query.get(session["user_id"])
    return render_template("dashboard.html", user=user)


@main_bp.route("/transactions")
@login_required
def transactions():
    user = User.query.get(session["user_id"])
    page = request.args.get("page", 1, type=int)
    category = request.args.get("category")
    search = request.args.get("search")
    sort = request.args.get("sort", "date_desc")

    query = Transaction.query.filter_by(user_id=user.id)

    if category and category != "all":
        query = query.filter_by(category=category)
    if search:
        query = query.filter(
            Transaction.description.ilike(f"%{search}%") |
            Transaction.merchant.ilike(f"%{search}%")
        )

    if sort == "date_asc":
        query = query.order_by(Transaction.date.asc())
    elif sort == "amount_desc":
        query = query.order_by(Transaction.amount.desc())
    elif sort == "amount_asc":
        query = query.order_by(Transaction.amount.asc())
    else:
        query = query.order_by(Transaction.date.desc())

    pagination = query.paginate(page=page, per_page=20, error_out=False)
    categories = get_category_data()

    return render_template(
        "transactions.html",
        user=user,
        transactions=pagination.items,
        pagination=pagination,
        categories=categories,
        current_category=category or "all",
        current_search=search or "",
        current_sort=sort,
    )


@main_bp.route("/summary")
@login_required
def summary():
    user = User.query.get(session["user_id"])
    year = request.args.get("year", datetime.now().year, type=int)
    month = request.args.get("month", datetime.now().month, type=int)

    transactions = Transaction.query.filter_by(user_id=user.id).filter(
        extract("year", Transaction.date) == year,
        extract("month", Transaction.date) == month,
    ).all()

    total_spent = sum(t.amount for t in transactions if not t.is_income)
    total_income = sum(t.amount for t in transactions if t.is_income)

    category_breakdown = {}
    for t in transactions:
        if not t.is_income:
            category_breakdown[t.category] = category_breakdown.get(t.category, 0) + t.amount

    categories = get_category_data()
    categories_list = []
    for cat, amount in sorted(category_breakdown.items(), key=lambda x: x[1], reverse=True):
        cat_info = categories.get(cat, {"icon": "circle", "color": "#94a3b8"})
        categories_list.append({
            "name": cat,
            "amount": round(amount, 2),
            "percentage": round(amount / total_spent * 100, 1) if total_spent > 0 else 0,
            "icon": cat_info["icon"],
            "color": cat_info["color"],
        })

    monthly_totals = []
    for m in range(1, 13):
        monthly = Transaction.query.filter_by(user_id=user.id).filter(
            extract("year", Transaction.date) == year,
            extract("month", Transaction.date) == m,
        ).all()
        spent = sum(t.amount for t in monthly if not t.is_income)
        income = sum(t.amount for t in monthly if t.is_income)
        monthly_totals.append({"month": m, "spent": round(spent, 2), "income": round(income, 2)})

    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    prev_transactions = Transaction.query.filter_by(user_id=user.id).filter(
        extract("year", Transaction.date) == prev_year,
        extract("month", Transaction.date) == prev_month,
    ).all()
    prev_spent = sum(t.amount for t in prev_transactions if not t.is_income)
    spent_change = ((total_spent - prev_spent) / prev_spent * 100) if prev_spent > 0 else 0

    return render_template(
        "summary.html",
        user=user,
        year=year,
        month=month,
        total_spent=round(total_spent, 2),
        total_income=round(total_income, 2),
        categories=categories_list,
        monthly_totals=monthly_totals,
        spent_change=round(spent_change, 1),
        transaction_count=len(transactions),
    )


@main_bp.route("/settings")
@login_required
def settings():
    user = User.query.get(session["user_id"])
    categories = get_category_data()
    rules = CategoryRule.query.filter(
        (CategoryRule.user_id == user.id) | (CategoryRule.is_global == True)
    ).all()
    return render_template("settings.html", user=user, categories=categories, rules=rules)


@main_bp.route("/sync")
@login_required
def sync():
    user = User.query.get(session["user_id"])
    if not user.google_token:
        flash("Please connect your Gmail account first.", "warning")
        return redirect(url_for("main.settings"))

    try:
        service, creds = get_gmail_service(user.google_token)

        user.google_token = json.dumps({
            "token": creds.token,
            "refresh_token": creds.refresh_token,
            "token_uri": creds.token_uri,
            "client_id": creds.client_id,
            "client_secret": creds.client_secret,
            "scopes": creds.scopes,
        })
        db.session.commit()

        messages = fetch_transaction_emails(service, days_back=30)
        logger.info(f"Fetched {len(messages)} messages from Gmail")

        existing_ids = set(
            t.email_message_id
            for t in Transaction.query.filter(
                Transaction.user_id == user.id,
                Transaction.email_message_id.isnot(None),
            ).all()
        )
        logger.info(f"Found {len(existing_ids)} existing transaction message IDs")

        import time

        new_count = 0
        error_count = 0
        skipped_no_amount = 0
        skipped_no_details = 0
        skipped_existing = 0

        for msg in messages:
            if msg["id"] in existing_ids:
                skipped_existing += 1
                continue

            try:
                time.sleep(0.05)
                email_data = get_message_details(service, msg["id"])
                if email_data is None:
                    skipped_no_details += 1
                    logger.debug(f"Skipped msg {msg['id']}: get_message_details returned None")
                    continue

                parsed = parse_transaction_email(email_data)
                if parsed is None:
                    skipped_no_amount += 1
                    subject_preview = email_data.get("subject", "")[:60]
                    logger.debug(f"Skipped msg {msg['id']} ({subject_preview}): no amount found")
                    continue

                category = categorize(parsed["merchant"], parsed["description"], parsed["is_income"])

                txn = Transaction(
                    user_id=user.id,
                    email_message_id=msg["id"],
                    date=parsed["date"],
                    description=parsed["description"],
                    amount=parsed["amount"],
                    currency=parsed["currency"],
                    category=category,
                    merchant=parsed["merchant"],
                    source_email=parsed["source_email"],
                    is_income=parsed["is_income"],
                )
                db.session.add(txn)
                new_count += 1
            except Exception as e:
                error_count += 1
                logger.warning(f"Error processing msg {msg['id']}: {e}")
                continue

        logger.info(
            f"Sync results: {new_count} new, {skipped_existing} existing, "
            f"{skipped_no_details} no details, {skipped_no_amount} no amount, "
            f"{error_count} errors"
        )

        user.last_sync_at = datetime.now(timezone.utc)
        db.session.commit()

        parts = [f"Found {new_count} new transactions."]
        if skipped_existing:
            parts.append(f"{skipped_existing} already synced")
        if skipped_no_amount:
            parts.append(f"{skipped_no_amount} unrecognized format")
        if error_count:
            parts.append(f"{error_count} errors")
        flash("Synced successfully! " + " ".join(parts), "success")
    except Exception as e:
        flash(f"Sync failed: {str(e)}", "error")

    return redirect(url_for("main.dashboard"))


@main_bp.route("/transactions/<int:txn_id>/delete", methods=["POST"])
@login_required
def delete_transaction(txn_id):
    txn = Transaction.query.get_or_404(txn_id)
    if txn.user_id != session["user_id"]:
        return {"error": "Unauthorized"}, 403
    db.session.delete(txn)
    db.session.commit()
    flash("Transaction deleted.", "info")
    return redirect(url_for("main.transactions"))


@main_bp.route("/transactions/<int:txn_id>/update-category", methods=["POST"])
@login_required
def update_category(txn_id):
    txn = Transaction.query.get_or_404(txn_id)
    if txn.user_id != session["user_id"]:
        return {"error": "Unauthorized"}, 403
    data = request.get_json()
    txn.category = data.get("category", txn.category)
    db.session.commit()
    return {"success": True}

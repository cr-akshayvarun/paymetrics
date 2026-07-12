from datetime import datetime, timezone
from flask import Blueprint, jsonify, request, session
from sqlalchemy import extract, func

from models import db, User, Transaction, CategoryRule
from services.categorizer import get_category_data

api_bp = Blueprint("api", __name__)


def login_required_api(f):
    from functools import wraps

    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)

    return decorated


@api_bp.route("/api/stats")
@login_required_api
def api_stats():
    user = User.query.get(session["user_id"])
    year = request.args.get("year", datetime.now().year, type=int)
    month = request.args.get("month", datetime.now().month, type=int)

    transactions = Transaction.query.filter_by(user_id=user.id).filter(
        extract("year", Transaction.date) == year,
        extract("month", Transaction.date) == month,
    ).all()

    total_spent = round(sum(t.amount for t in transactions if not t.is_income), 2)
    total_income = round(sum(t.amount for t in transactions if t.is_income), 2)

    category_breakdown = {}
    for t in transactions:
        if not t.is_income:
            category_breakdown[t.category] = round(
                category_breakdown.get(t.category, 0) + t.amount, 2
            )

    recent = (
        Transaction.query.filter_by(user_id=user.id)
        .order_by(Transaction.date.desc())
        .limit(5)
        .all()
    )

    monthly_spent = []
    monthly_income = []
    for m in range(1, 13):
        monthly = Transaction.query.filter_by(user_id=user.id).filter(
            extract("year", Transaction.date) == year,
            extract("month", Transaction.date) == m,
        ).all()
        monthly_spent.append(round(sum(t.amount for t in monthly if not t.is_income), 2))
        monthly_income.append(round(sum(t.amount for t in monthly if t.is_income), 2))

    return jsonify({
        "total_spent": total_spent,
        "total_income": total_income,
        "net_savings": round(total_income - total_spent, 2),
        "transaction_count": len(transactions),
        "category_breakdown": category_breakdown,
        "recent_transactions": [t.to_dict() for t in recent],
        "monthly_spent": monthly_spent,
        "monthly_income": monthly_income,
    })


@api_bp.route("/api/transactions")
@login_required_api
def api_transactions():
    user = User.query.get(session["user_id"])
    transactions = (
        Transaction.query.filter_by(user_id=user.id)
        .order_by(Transaction.date.desc())
        .limit(50)
        .all()
    )
    return jsonify([t.to_dict() for t in transactions])


@api_bp.route("/api/categories")
@login_required_api
def api_categories():
    return jsonify(get_category_data())

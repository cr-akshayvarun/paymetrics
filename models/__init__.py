from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone
import json

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    name = db.Column(db.String(255))
    google_token = db.Column(db.Text, nullable=True)
    avatar_url = db.Column(db.String(512))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    last_sync_at = db.Column(db.DateTime, nullable=True)

    transactions = db.relationship("Transaction", backref="user", lazy="dynamic", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "email": self.email,
            "name": self.name,
            "avatar_url": self.avatar_url,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_sync_at": self.last_sync_at.isoformat() if self.last_sync_at else None,
        }


class Transaction(db.Model):
    __tablename__ = "transactions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    email_message_id = db.Column(db.String(255))
    date = db.Column(db.DateTime, nullable=False)
    description = db.Column(db.Text)
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(10), default="INR")
    category = db.Column(db.String(100), default="Other")
    merchant = db.Column(db.String(255))
    source_email = db.Column(db.String(255))
    is_income = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "id": self.id,
            "date": self.date.strftime("%Y-%m-%d") if self.date else None,
            "description": self.description,
            "amount": self.amount,
            "currency": self.currency,
            "category": self.category,
            "merchant": self.merchant,
            "source_email": self.source_email,
            "is_income": self.is_income,
        }


class CategoryRule(db.Model):
    __tablename__ = "category_rules"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    category = db.Column(db.String(100), nullable=False)
    keywords = db.Column(db.Text, nullable=False)
    is_global = db.Column(db.Boolean, default=True)

    def to_dict(self):
        return {
            "id": self.id,
            "category": self.category,
            "keywords": json.loads(self.keywords),
            "is_global": self.is_global,
        }

# PayMetrics — Personal Expense Tracker

A personal finance web app that connects to your Gmail via OAuth, fetches transaction emails (receipts, bank notifications), and automatically categorizes them into spending buckets. View your finances on an interactive dashboard with monthly trends, category breakdowns, and transaction history.

## Tech Stack

| | |
|---|---|
| Backend | Python, Flask, Flask-SQLAlchemy |
| API | Google Gmail API (OAuth 2.0) |
| Parser | Regex-based email extraction |
| DB | SQLite |

## Features

- **Gmail Sync** — OAuth 2.0 integration to fetch transaction emails
- **Auto-Parse** — Extracts amount, merchant, date, and currency from email bodies
- **Smart Categorization** — Keyword-based rules for Food, Shopping, Transport, Bills, Entertainment, Healthcare, Education, Income
- **Dashboard** — Spending breakdowns, monthly trends, and recent transactions
- **Transaction Management** — View, search, filter, sort, delete, and recategorize
- **Monthly Summary** — Compare spending vs income with month-over-month changes
- **Custom Rules** — Define your own categorization rules per merchant/keyword

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Configure Google OAuth credentials
# Edit credentials.json with your Google Cloud project credentials

# Run
python app.py
# → http://localhost:5001
```

## API

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/stats` | Spending stats for a given month/year |
| GET | `/api/transactions` | Recent transactions (last 50) |
| GET | `/api/categories` | Category definitions and icons |

## Pages

| Route | Description |
|---|---|
| `/` | Home / landing page |
| `/dashboard` | Main spending dashboard with charts |
| `/transactions` | Full transaction list with search & filters |
| `/summary` | Monthly spending summary with trends |
| `/settings` | Gmail connection, categories, rules |
| `/auth/login` | Google OAuth login |
| `/sync` | Trigger Gmail email sync |

import re
from datetime import datetime
from email.utils import parsedate_to_datetime

AMOUNT_PATTERNS = [
    r"(?:Rs\.?|INR|₹)\s*([0-9,]+\.?\d*)",
    r"(?:USD|\$)\s*([0-9,]+\.?\d*)",
    r"(?:EUR|€)\s*([0-9,]+\.?\d*)",
    r"(?:GBP|£)\s*([0-9,]+\.?\d*)",
    r"INR\.\s*([0-9,]+\.?\d*)",
    r"(?:amount|amt)[:\s.]*[₹$€£]?\s*([0-9,]+\.?\d*)",
    r"(?:total)[:\s.]*[₹$€£]?\s*([0-9,]+\.?\d*)",
    r"(?:charged|debited|paid|spent|credited)[:\s]*[₹$€£]?\s*([0-9,]+\.?\d*)",
    r"(?:of|for)[:\s]*[₹$€£]\s*([0-9,]+\.?\d*)",
    r"(?:sent|received|paid|transferred)[:\s]*[₹$€£]?\s*([0-9,]+\.?\d*)",
    r"(?:debit|credit|payment|transaction|purchase)\s+(?:of|for|:)\s*[₹$€£]?\s*([0-9,]+\.?\d*)",
    r"[₹$€£]\s*([0-9,]+\.?\d*)",
]

MERCHANT_PATTERNS = [
    r"(?:at|to|from|merchant|vendor|payee)[:\s]+([A-Za-z0-9\s\.&'\-]+?)(?:\s+(?:on|dated|ref|via|using|with|for|₹|\$|€|£|[0-9]|$))",
    r"(?:spent at|purchase at|payment to|paid to|sent to|transferred to)\s+([A-Za-z0-9\s\.&'\-]+?)(?:\s+(?:on|dated|ref|via|using|with|for|₹|\$|€|£|[0-9]|$))",
    r"(?:payee|beneficiary)[:\s]+([A-Za-z0-9\s\.&'\-]+)",
]

DESCRIPTION_CLEANUP = [
    (r"Your (?:UPI|card|account|debit|credit|net banking)\s+(?:transaction|payment|debit|credit)\s+", "", re.IGNORECASE),
    (r"Dear\s+(?:Customer|User|MR|Ms|Mrs)\.?\s*\w*,?\s*", "", re.IGNORECASE),
    (r"<[^>]+>", " ", 0),
    (r"\s+", " ", 0),
    (r"^\s*[:\-,\s]+", "", 0),
]

INCOME_KEYWORDS = [
    "credited", "received", "salary", "refund", "cashback", "deposit",
    "interest", "income", "payment received", "money received", "credit",
    "reversed", "added to",
]


def extract_amount(text):
    for pattern in AMOUNT_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            raw = match.group(1).replace(",", "").strip()
            try:
                val = float(raw)
                if 1 <= val <= 99999999:
                    return val
            except ValueError:
                continue
    return None


def extract_merchant(text):
    for pattern in MERCHANT_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            merchant = match.group(1).strip().rstrip(".")
            if len(merchant) > 2:
                return merchant
    return None


def extract_description(subject, body):
    combined = f"{subject} {body[:500]}"
    desc = combined.strip()
    for pattern, replacement, flags in DESCRIPTION_CLEANUP:
        desc = re.sub(pattern, replacement, desc, flags=flags)
    desc = desc.strip()[:200]
    if not desc:
        desc = subject.strip()[:200]
    return desc if desc else "Unknown Transaction"


def extract_date(email_date_str):
    try:
        dt = parsedate_to_datetime(email_date_str)
        return dt
    except Exception:
        return datetime.utcnow()


def detect_is_income(subject, body):
    text = f"{subject} {body[:300]}".lower()
    for kw in INCOME_KEYWORDS:
        if kw in text:
            return True
    return False


def detect_currency(text):
    if re.search(r"(?:Rs\.?|INR|₹)", text, re.IGNORECASE):
        return "INR"
    if re.search(r"(?:USD|\$)", text, re.IGNORECASE):
        return "USD"
    if re.search(r"(?:EUR|€)", text, re.IGNORECASE):
        return "EUR"
    if re.search(r"(?:GBP|£)", text, re.IGNORECASE):
        return "GBP"
    return "INR"


def parse_transaction_email(email_data):
    subject = email_data.get("subject", "")
    body = email_data.get("body", "")
    from_addr = email_data.get("from", "")
    date_str = email_data.get("date", "")

    text = f"{subject}\n\n{body}"

    amount = extract_amount(text)
    if amount is None:
        return None

    merchant = extract_merchant(text)
    if merchant is None:
        if "<" in from_addr:
            merchant = from_addr.split("<")[0].strip()
        else:
            merchant = from_addr.split("@")[0].strip()
        merchant = merchant.replace('"', "").replace("'", "").strip()
        if not merchant or len(merchant) < 2:
            merchant = subject.split(":")[0].strip() if ":" in subject else subject[:30].strip()

    description = extract_description(subject, body)
    date = extract_date(date_str)
    currency = detect_currency(text)
    is_income = detect_is_income(subject, body)

    return {
        "amount": amount,
        "description": description,
        "merchant": merchant,
        "date": date,
        "currency": currency,
        "is_income": is_income,
        "source_email": from_addr,
    }

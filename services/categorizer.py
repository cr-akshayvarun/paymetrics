import json
import re
from models import CategoryRule, db

DEFAULT_CATEGORIES = {
    "Food & Dining": {
        "icon": "utensils",
        "color": "#f97316",
        "keywords": [
            "zomato", "swiggy", "uber eats", "restaurant", "pizza", "burger",
            "kfc", "mcdonald", "dominos", "subway", "starbucks", "cafe",
            "dining", "food", "grocery", "bigbasket", "blinkit", "zepto",
            "dmart", "supermarket", "bakery", "hotel", "meal", "lunch", "dinner",
        ],
    },
    "Shopping": {
        "icon": "shopping-bag",
        "color": "#ec4899",
        "keywords": [
            "amazon", "flipkart", "myntra", "ajio", "nykaa", "meesho",
            "shop", "store", "mall", "retail", "cloth", "apparel", "footwear",
            "electronics", "lifestyle", "brand", "purchase", "order",
            "amazon pay", "paytm mall",
        ],
    },
    "Transportation": {
        "icon": "car",
        "color": "#3b82f6",
        "keywords": [
            "uber", "ola", "rapido", "metro", "bus", "train", "flight",
            "fuel", "petrol", "diesel", "indian oil", "bharat petroleum",
            "hp petrol", "parking", "taxi", "cab", "auto", "toll",
            "irctc", "make my trip", "goibibo", "redbus",
        ],
    },
    "Bills & Utilities": {
        "icon": "file-invoice",
        "color": "#8b5cf6",
        "keywords": [
            "electricity", "water bill", "gas bill", "broadband", "wifi",
            "internet", "mobile recharge", "phone bill", "electric bill",
            "utility", "bill payment", "rent", "maintenance", "society",
            "bsnl", "airtel", "jio", "vi", "vodafone", "tata power",
            "adani", "electricity board",
        ],
    },
    "Entertainment": {
        "icon": "film",
        "color": "#14b8a6",
        "keywords": [
            "netflix", "prime video", "hotstar", "disney", "sonyliv",
            "zomato", "book my show", "paytm movies", "theater", "cinema",
            "movie", "concert", "spotify", "youtube premium", "music",
            "game", "gaming", "steam", "playstation", "xbox",
        ],
    },
    "Healthcare": {
        "icon": "heartbeat",
        "color": "#ef4444",
        "keywords": [
            "hospital", "clinic", "doctor", "pharmacy", "medicine",
            "medical", "health", "diagnostic", "lab", "pathology",
            "dentist", "ayurveda", "health insurance", "chemist",
            "apollo", "fortis", "medlife", "practo", "pharmeasy",
            "1mg", "netmeds",
        ],
    },
    "Education": {
        "icon": "graduation-cap",
        "color": "#f59e0b",
        "keywords": [
            "tuition", "college", "university", "school", "course",
            "udemy", "coursera", "vedantu", "byjus", "unacademy",
            "book", "library", "exam fee", "admission", "hostel fee",
            "online course", "certification", "training", "class",
        ],
    },
    "Income": {
        "icon": "wallet",
        "color": "#10b981",
        "keywords": [
            "salary", "credit", "received", "income", "payment received",
            "refund", "cashback", "deposit", "interest", "dividend",
            "freelance", "invoice payment", "client payment",
        ],
    },
}


def load_default_rules():
    for category, data in DEFAULT_CATEGORIES.items():
        existing = CategoryRule.query.filter_by(category=category, is_global=True).first()
        if not existing:
            rule = CategoryRule(
                category=category,
                keywords=json.dumps(data["keywords"]),
                is_global=True,
            )
            db.session.add(rule)
    db.session.commit()


def categorize(merchant, description, is_income=False):
    if is_income:
        return "Income"

    text = f"{merchant} {description}".lower()

    rules = CategoryRule.query.filter_by(is_global=True).all()
    best_category = "Other"
    best_score = 0

    for rule in rules:
        keywords = json.loads(rule.keywords)
        score = 0
        for keyword in keywords:
            if keyword.lower() in text:
                score += 1
        if score > best_score:
            best_score = score
            best_category = rule.category

    if "." in (merchant or "") and "@" not in (merchant or ""):
        parts = (merchant or "").split(".")
        if len(parts) >= 2:
            domain = parts[-2].strip().lower()
            for rule in rules:
                keywords = json.loads(rule.keywords)
                for kw in keywords:
                    if kw in domain:
                        return rule.category

    return best_category


def get_category_data():
    categories = DEFAULT_CATEGORIES.copy()
    categories["Other"] = {"icon": "circle", "color": "#94a3b8", "keywords": []}
    user_rules = CategoryRule.query.filter_by(is_global=False).all()
    for rule in user_rules:
        category = rule.category
        if category not in categories:
            categories[category] = {"icon": "circle", "color": "#6366f1", "keywords": []}
        categories[category]["keywords"].extend(json.loads(rule.keywords))
    return categories

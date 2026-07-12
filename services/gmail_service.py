import os
import re
import json
import base64
import html
import time
import logging
from datetime import datetime, timezone, timedelta
from email import message_from_bytes

logger = logging.getLogger(__name__)

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from config import Config


def get_gmail_service(user_token_json):
    creds_data = json.loads(user_token_json)
    creds = Credentials.from_authorized_user_info(creds_data, Config.GMAIL_SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            raise Exception("Invalid credentials")
    return build("gmail", "v1", credentials=creds), creds


def create_oauth_flow():
    flow = Flow.from_client_secrets_file(
        Config.CREDENTIALS_FILE,
        scopes=Config.GMAIL_SCOPES,
        redirect_uri=Config.GOOGLE_REDIRECT_URI,
    )
    return flow


def fetch_transaction_emails(service, days_back=30):
    after_date = (datetime.now(timezone.utc) - timedelta(days=days_back)).strftime("%Y/%m/%d")

    query = f"after:{after_date}"
    logger.info(f"Gmail query: {query}")

    messages = []
    page_token = None
    while True:
        results = (
            service.users()
            .messages()
            .list(userId="me", q=query, pageToken=page_token, maxResults=200)
            .execute()
        )
        batch = results.get("messages", [])
        messages.extend(batch)
        page_token = results.get("nextPageToken")
        if not page_token:
            break

    return messages


def _decode_payload(part):
    payload = part.get_payload(decode=True)
    if payload is None:
        return ""
    try:
        return payload.decode("utf-8", errors="ignore")
    except Exception:
        try:
            return payload.decode("latin-1", errors="ignore")
        except Exception:
            return ""


def _strip_html(text):
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL)
    text = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"&amp;", "&", text)
    text = re.sub(r"&lt;", "<", text)
    text = re.sub(r"&gt;", ">", text)
    text = re.sub(r"&[a-zA-Z]+;", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def get_message_details(service, msg_id):
    try:
        msg = (
            service.users()
            .messages()
            .get(userId="me", id=msg_id, format="raw")
            .execute()
        )
    except HttpError:
        return None

    raw_data = msg.get("raw", "")
    if not raw_data:
        return None

    try:
        email_bytes = base64.urlsafe_b64decode(raw_data.encode("ASCII"))
    except Exception:
        return None

    mime_msg = message_from_bytes(email_bytes)

    subject = mime_msg["subject"] or ""
    from_addr = mime_msg["from"] or ""
    date_str = mime_msg["date"] or ""

    body = ""
    if mime_msg.is_multipart():
        plain_body = ""
        html_body = ""
        for part in mime_msg.walk():
            ct = part.get_content_type()
            if ct == "text/plain":
                plain_body = _decode_payload(part)
            elif ct == "text/html":
                raw = _decode_payload(part)
                if raw:
                    html_body = _strip_html(raw)
        body = html_body if len(html_body) > len(plain_body) else plain_body
    else:
        ct = mime_msg.get_content_type()
        body = _decode_payload(mime_msg)
        if not body and ct == "text/html":
            body = _strip_html(_decode_payload(mime_msg))

    return {
        "id": msg_id,
        "subject": subject,
        "from": from_addr,
        "date": date_str,
        "body": body,
    }

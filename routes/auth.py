import json
from flask import Blueprint, redirect, request, session, url_for, flash
from models import db, User
from services.gmail_service import create_oauth_flow
from google.auth.transport.requests import Request

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login")
def login():
    flow = create_oauth_flow()
    authorization_url, state = flow.authorization_url(
        access_type="offline", include_granted_scopes="true", prompt="consent"
    )
    session["oauth_state"] = state
    return redirect(authorization_url)


@auth_bp.route("/auth/callback")
def callback():
    state = session.get("oauth_state")
    if not state:
        flash("Session expired. Please try again.", "error")
        return redirect(url_for("main.home"))

    flow = create_oauth_flow()
    flow.fetch_token(authorization_response=request.url)

    creds = flow.credentials
    if not creds.valid:
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())

    from googleapiclient.discovery import build

    service = build("oauth2", "v2", credentials=creds)
    user_info = service.userinfo().get().execute()

    email = user_info.get("email")
    name = user_info.get("name")
    avatar = user_info.get("picture")

    token_json = json.dumps({
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": creds.scopes,
    })

    user = User.query.filter_by(email=email).first()
    if user:
        user.google_token = token_json
        user.name = name or user.name
        user.avatar_url = avatar or user.avatar_url
    else:
        user = User(
            email=email,
            name=name,
            avatar_url=avatar,
            google_token=token_json,
        )
        db.session.add(user)

    db.session.commit()
    session["user_id"] = user.id
    session["user_email"] = user.email
    session["user_name"] = user.name
    session["user_avatar"] = user.avatar_url

    flash("Successfully connected your Gmail account!", "success")
    return redirect(url_for("main.dashboard"))


@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully.", "info")
    return redirect(url_for("main.home"))

from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from jose import jwt
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.plans import FREE_PLAN
from app.models.user import User
from app.schemas.auth import AuthResponse


def create_access_token(user_id: int) -> str:
    payload = {
        "sub": str(user_id),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def _auth_response_for_user(user: User) -> AuthResponse:
    return AuthResponse(access_token=create_access_token(user.id), user=user)


def register_with_email(db: Session, name: str, email: str) -> AuthResponse:
    normalized_name = name.strip()
    normalized_email = email.strip().lower()
    existing_user = db.query(User).filter(or_(User.email == normalized_email, User.name == normalized_name)).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Account already exists. Please log in.",
        )

    user = User(
        google_id=None,
        name=normalized_name,
        email=normalized_email,
        avatar=None,
        plan=FREE_PLAN,
        subscription_status="free",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return _auth_response_for_user(user)


def login_with_email(db: Session, email: str) -> AuthResponse:
    normalized_email = email.strip().lower()
    user = db.query(User).filter(User.email == normalized_email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found. Please create an account first.",
        )
    return _auth_response_for_user(user)


def login_with_google(db: Session, credential: str) -> AuthResponse:
    try:
        token_info = id_token.verify_oauth2_token(credential, google_requests.Request(), settings.google_client_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Google credential") from exc
    google_id = token_info["sub"]
    email = token_info["email"].strip().lower()

    user = db.query(User).filter(User.google_id == google_id).first()
    if not user:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            user = User(
                google_id=google_id,
                name=token_info.get("name", email.split("@")[0]),
                email=email,
                avatar=token_info.get("picture"),
                plan=FREE_PLAN,
                subscription_status="free",
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            return _auth_response_for_user(user)

    user.google_id = google_id
    user.name = token_info.get("name", user.name)
    user.avatar = token_info.get("picture", user.avatar)
    user.email = email
    db.add(user)
    db.commit()
    db.refresh(user)

    return _auth_response_for_user(user)

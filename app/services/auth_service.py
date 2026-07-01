from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from jose import jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.plans import FREE_PLAN
from app.models.user import User
from app.schemas.auth import AuthResponse

password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_access_token(user_id: int) -> str:
    payload = {
        "sub": str(user_id),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def _auth_response_for_user(user: User) -> AuthResponse:
    return AuthResponse(access_token=create_access_token(user.id), user=user)


def hash_password(password: str) -> str:
    return password_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return password_context.verify(password, password_hash)


def register_with_email(db: Session, name: str, email: str, password: str) -> AuthResponse:
    normalized_name = name.strip()
    normalized_email = email.strip().lower()
    existing_user = db.query(User).filter(User.email == normalized_email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Account already exists. Please log in.",
        )

    user = User(
        google_id=None,
        name=normalized_name,
        email=normalized_email,
        password_hash=hash_password(password),
        avatar=None,
        plan=FREE_PLAN,
        subscription_status="free",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return _auth_response_for_user(user)


def login_with_email(db: Session, email: str, password: str) -> AuthResponse:
    normalized_email = email.strip().lower()
    user = db.query(User).filter(User.email == normalized_email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found. Please create an account first.",
        )

    if not user.password_hash:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This account does not have a password yet. Continue with Google to sign in.",
        )

    if not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect password.",
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

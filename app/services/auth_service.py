from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from jose import jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.user import User
from app.schemas.auth import AuthResponse


def create_access_token(user_id: int) -> str:
    payload = {
        "sub": str(user_id),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def login_with_google(db: Session, credential: str) -> AuthResponse:
    try:
        token_info = id_token.verify_oauth2_token(credential, google_requests.Request(), settings.google_client_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Google credential") from exc
    google_id = token_info["sub"]
    email = token_info["email"]

    user = db.query(User).filter(User.google_id == google_id).first()
    if not user:
        user = User(
            google_id=google_id,
            name=token_info.get("name", email.split("@")[0]),
            email=email,
            avatar=token_info.get("picture"),
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        user.name = token_info.get("name", user.name)
        user.avatar = token_info.get("picture", user.avatar)
        db.add(user)
        db.commit()
        db.refresh(user)

    return AuthResponse(access_token=create_access_token(user.id), user=user)

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import AuthResponse, EmailLoginRequest, EmailRegisterRequest, GoogleAuthRequest, UserResponse
from app.services.auth_service import login_with_email, login_with_google, register_with_email

router = APIRouter()


@router.post("/google", response_model=AuthResponse)
def google_auth(payload: GoogleAuthRequest, db: Session = Depends(get_db)) -> AuthResponse:
    return login_with_google(db=db, credential=payload.credential)


@router.post("/register", response_model=AuthResponse)
def register_auth(payload: EmailRegisterRequest, db: Session = Depends(get_db)) -> AuthResponse:
    return register_with_email(db=db, name=payload.name, email=payload.email, password=payload.password)


@router.post("/login", response_model=AuthResponse)
def login_auth(payload: EmailLoginRequest, db: Session = Depends(get_db)) -> AuthResponse:
    return login_with_email(db=db, email=payload.email, password=payload.password)


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)) -> UserResponse:
    return current_user

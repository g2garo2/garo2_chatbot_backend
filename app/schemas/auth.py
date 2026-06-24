from datetime import datetime

from pydantic import BaseModel, EmailStr


class GoogleAuthRequest(BaseModel):
    credential: str


class UserResponse(BaseModel):
    id: int
    google_id: str
    name: str
    email: EmailStr
    avatar: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

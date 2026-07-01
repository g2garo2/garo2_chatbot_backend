from datetime import datetime

from pydantic import BaseModel, EmailStr, field_validator


class GoogleAuthRequest(BaseModel):
    credential: str


class UserResponse(BaseModel):
    id: int
    google_id: str | None
    name: str
    email: EmailStr
    avatar: str | None
    plan: str
    subscription_status: str
    razorpay_subscription_id: str | None
    razorpay_customer_id: str | None
    subscription_start: datetime | None
    subscription_end: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class EmailRegisterRequest(BaseModel):
    name: str
    email: EmailStr

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Name is required")
        return normalized


class EmailLoginRequest(BaseModel):
    email: EmailStr

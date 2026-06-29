from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class AccountDeletionRequestCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    reason: str = Field(min_length=1, max_length=5000)


class AccountDeletionRequestResponse(BaseModel):
    id: int
    name: str
    email: EmailStr
    reason: str
    created_at: datetime

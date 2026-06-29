from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class FeedbackRequestCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    feedback_type: str = Field(min_length=1, max_length=50)
    message: str = Field(min_length=1, max_length=5000)


class FeedbackRequestResponse(BaseModel):
    id: int
    name: str
    email: EmailStr
    feedback_type: str
    message: str
    created_at: datetime

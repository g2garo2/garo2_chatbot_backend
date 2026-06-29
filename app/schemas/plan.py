from datetime import datetime

from pydantic import BaseModel, Field


class SubscriptionPlanBase(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    price: int = Field(ge=0)
    billing_cycle: str = Field(min_length=1, max_length=30)
    chat_limit: int | None = Field(default=None, ge=0)
    translation_limit: int = Field(ge=0)
    ai_provider: str = Field(min_length=1, max_length=2000)
    button_text: str = Field(min_length=1, max_length=255)
    is_popular: bool = False
    is_active: bool = True
    sort_order: int = 0


class SubscriptionPlanCreateRequest(SubscriptionPlanBase):
    plan_key: str = Field(min_length=1, max_length=50, pattern=r"^[a-z0-9_-]+$")


class SubscriptionPlanUpdateRequest(SubscriptionPlanBase):
    pass


class SubscriptionPlanResponse(SubscriptionPlanBase):
    id: int
    plan_key: str
    created_at: datetime
    updated_at: datetime


class PublicSubscriptionPlanResponse(BaseModel):
    id: int
    plan_key: str
    name: str
    price: int
    billing_cycle: str
    chat_limit: int | None
    translation_limit: int
    ai_provider: str
    button_text: str
    is_popular: bool
    sort_order: int

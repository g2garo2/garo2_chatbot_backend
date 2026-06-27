from pydantic import BaseModel


class UsageLimitView(BaseModel):
    used: int
    limit: int | None
    remaining: int | None


class UsageResponse(BaseModel):
    plan: str
    chat: UsageLimitView
    translation: UsageLimitView
    image_upload: UsageLimitView
    image_generation: UsageLimitView

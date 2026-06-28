from pydantic import BaseModel, Field


class DefaultPromptUpdateRequest(BaseModel):
    prompt: str = Field(default="", max_length=12000)


class DefaultPromptResponse(BaseModel):
    prompt: str
    updated_at: str | None = None

from pydantic import BaseModel, Field


class DefaultPromptUpdateRequest(BaseModel):
    prompt: str = Field(default="", max_length=12000)


class DefaultPromptResponse(BaseModel):
    prompt: str
    updated_at: str | None = None


class PromptSuggestionsUpdateRequest(BaseModel):
    prompts: list[str] = Field(default_factory=list, min_length=1, max_length=6)


class PromptSuggestionsResponse(BaseModel):
    prompts: list[str] = Field(default_factory=list)
    updated_at: str | None = None

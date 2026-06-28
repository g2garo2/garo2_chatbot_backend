from datetime import datetime

from pydantic import BaseModel, Field


class ChatCreateRequest(BaseModel):
    title: str | None = None


class ChatHistoryItem(BaseModel):
    id: int
    user_id: int
    title: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MessageResponse(BaseModel):
    id: int
    chat_id: int
    role: str
    content: str
    image_url: str | None
    input_language: str
    output_language: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatDetailResponse(ChatHistoryItem):
    messages: list[MessageResponse] = Field(default_factory=list)


class ChatMessageRequest(BaseModel):
    content: str = ""
    image_url: str | None = None
    input_language: str = "english"
    output_language: str = "english"


class ChatMessageResponse(BaseModel):
    user_message: MessageResponse
    assistant_message: MessageResponse
    chat: ChatHistoryItem


class PromptSuggestionsResponse(BaseModel):
    prompts: list[str] = Field(default_factory=list)

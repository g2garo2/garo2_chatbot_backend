from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.chat import Chat
from app.models.message import Message
from app.models.user import User
from app.schemas.chat import (
    ChatCreateRequest,
    ChatDetailResponse,
    ChatHistoryItem,
    ChatMessageRequest,
    ChatMessageResponse,
)
from app.services.ai_provider_service import generate_chat_for_user
from app.services.usage_service import enforce_chat_limit, increment_chat_usage

router = APIRouter()


@router.post("/new", response_model=ChatHistoryItem)
def create_chat(
    payload: ChatCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ChatHistoryItem:
    title = payload.title or "New Chat"
    chat = Chat(user_id=current_user.id, title=title)
    db.add(chat)
    db.commit()
    db.refresh(chat)
    return chat


@router.get("/history", response_model=list[ChatHistoryItem])
def chat_history(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[ChatHistoryItem]:
    return (
        db.query(Chat)
        .filter(Chat.user_id == current_user.id)
        .order_by(desc(Chat.updated_at))
        .all()
    )


@router.get("/{chat_id}", response_model=ChatDetailResponse)
def get_chat(chat_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> ChatDetailResponse:
    chat = db.query(Chat).filter(Chat.id == chat_id, Chat.user_id == current_user.id).first()
    if not chat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found")
    return chat


@router.post("/{chat_id}/message", response_model=ChatMessageResponse)
def post_message(
    chat_id: int,
    payload: ChatMessageRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ChatMessageResponse:
    chat = db.query(Chat).filter(Chat.id == chat_id, Chat.user_id == current_user.id).first()
    if not chat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found")
    if not payload.content.strip() and not payload.image_url:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Message text or image is required")

    enforce_chat_limit(db, current_user)
    prior_messages = db.query(Message).filter(Message.chat_id == chat.id).order_by(Message.created_at.asc()).all()
    pending_user_message = Message(
        chat_id=chat.id,
        role="user",
        content=payload.content.strip() or "Please analyze this image.",
        image_url=payload.image_url,
        input_language=payload.input_language,
        output_language=payload.output_language,
    )
    ai_content = generate_chat_for_user(
        user=current_user,
        messages=[*prior_messages, pending_user_message],
        input_language=payload.input_language,
        output_language=payload.output_language,
    )

    user_message = pending_user_message
    db.add(user_message)
    assistant_message = Message(
        chat_id=chat.id,
        role="assistant",
        content=ai_content,
        image_url=None,
        input_language=payload.input_language,
        output_language=payload.output_language,
    )
    db.add(assistant_message)
    chat.updated_at = datetime.now(timezone.utc)
    increment_chat_usage(db, current_user)

    if chat.title == "New Chat":
        chat.title = (payload.content.strip() or "Image Chat")[:60]
    db.add(chat)
    db.commit()
    db.refresh(user_message)
    db.refresh(assistant_message)
    db.refresh(chat)
    return ChatMessageResponse(user_message=user_message, assistant_message=assistant_message, chat=chat)


@router.delete("/{chat_id}")
def delete_chat(chat_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict[str, str]:
    chat = db.query(Chat).filter(Chat.id == chat_id, Chat.user_id == current_user.id).first()
    if not chat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found")
    db.delete(chat)
    db.commit()
    return {"message": "Chat deleted"}

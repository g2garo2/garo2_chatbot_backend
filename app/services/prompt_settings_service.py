from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.app_setting import AppSetting

DEFAULT_CHAT_PROMPT_KEY = "default_chat_prompt"
DEFAULT_CHAT_PROMPT_FALLBACK = "Be accurate, helpful, and concise while staying aligned with the user's requested language."


def get_default_prompt_setting(db: Session) -> AppSetting | None:
    return db.get(AppSetting, DEFAULT_CHAT_PROMPT_KEY)


def get_default_prompt_text(db: Session) -> str:
    setting = get_default_prompt_setting(db)
    if not setting:
        return DEFAULT_CHAT_PROMPT_FALLBACK
    return (setting.value or "").strip() or DEFAULT_CHAT_PROMPT_FALLBACK


def upsert_default_prompt(db: Session, prompt: str) -> AppSetting:
    normalized = prompt.strip() or DEFAULT_CHAT_PROMPT_FALLBACK
    setting = get_default_prompt_setting(db)
    if setting is None:
        setting = AppSetting(
            key=DEFAULT_CHAT_PROMPT_KEY,
            value=normalized,
            updated_at=datetime.now(timezone.utc),
        )
    else:
        setting.value = normalized
        setting.updated_at = datetime.now(timezone.utc)

    db.add(setting)
    db.commit()
    db.refresh(setting)
    return setting

import json
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.app_setting import AppSetting

DEFAULT_CHAT_PROMPT_KEY = "default_chat_prompt"
DEFAULT_CHAT_PROMPT_FALLBACK = "Be accurate, helpful, and concise while staying aligned with the user's requested language."
PROMPT_SUGGESTIONS_KEY = "prompt_suggestions"
PROMPT_SUGGESTIONS_FALLBACK = [
    "Tell me 10 interesting facts about Meghalaya's history, culture, festivals, tribes, and famous places in simple student-friendly language.",
    "Quiz me with 20 general knowledge questions about Meghalaya, including answers and short explanations.",
    "Explain Meghalaya district-wise with important facts about geography, people, culture, tourism, and current development for students.",
]


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


def get_prompt_suggestions_setting(db: Session) -> AppSetting | None:
    return db.get(AppSetting, PROMPT_SUGGESTIONS_KEY)


def get_prompt_suggestions(db: Session) -> list[str]:
    setting = get_prompt_suggestions_setting(db)
    if not setting or not (setting.value or "").strip():
        return PROMPT_SUGGESTIONS_FALLBACK.copy()

    try:
        parsed = json.loads(setting.value)
    except json.JSONDecodeError:
        return PROMPT_SUGGESTIONS_FALLBACK.copy()

    if not isinstance(parsed, list):
        return PROMPT_SUGGESTIONS_FALLBACK.copy()

    normalized = [str(item).strip() for item in parsed if str(item).strip()]
    return normalized or PROMPT_SUGGESTIONS_FALLBACK.copy()


def upsert_prompt_suggestions(db: Session, prompts: list[str]) -> AppSetting:
    normalized = [prompt.strip() for prompt in prompts if prompt.strip()]
    if not normalized:
        normalized = PROMPT_SUGGESTIONS_FALLBACK.copy()

    serialized = json.dumps(normalized, ensure_ascii=True)
    setting = get_prompt_suggestions_setting(db)
    if setting is None:
        setting = AppSetting(
            key=PROMPT_SUGGESTIONS_KEY,
            value=serialized,
            updated_at=datetime.now(timezone.utc),
        )
    else:
        setting.value = serialized
        setting.updated_at=datetime.now(timezone.utc)

    db.add(setting)
    db.commit()
    db.refresh(setting)
    return setting

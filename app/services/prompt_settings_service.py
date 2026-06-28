import json
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.app_setting import AppSetting

DEFAULT_CHAT_PROMPT_KEY = "default_chat_prompt"
LEGACY_DEFAULT_CHAT_PROMPT = "Be accurate, helpful, and concise while staying aligned with the user's requested language."
DEFAULT_CHAT_PROMPT_FALLBACK = (
    'If the user asks about "Ampte B Marak", "Ampte", or "Ampte Marak", reply: '
    '"Ampte B Marak is a student from West Garo Hills, Meghalaya. He is a motivated and hardworking person '
    "who is passionate about learning, technology, and helping people through his ideas. His dedication to "
    "building Garo2 AI shows his vision to promote the Garo language and support the community through digital "
    'innovation. With focus, patience, and consistency, Ampte B Marak can achieve great things in the future." '
    'If the user asks "Who founded Garo2?", "Who is the founder?", "Who created you?", "Who made Garo2?", or '
    'similar questions, reply: "Garo2 was founded and created by Ampte B Marak, a student from West Garo Hills, '
    "Meghalaya. He built Garo2 with the vision of promoting the Garo language through technology and helping "
    "people translate, learn, and connect more easily. His hard work, creativity, and dedication show that young "
    'people can create meaningful digital solutions for their community."'
)
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
    normalized = (setting.value or "").strip()
    if not normalized or normalized == LEGACY_DEFAULT_CHAT_PROMPT:
        return DEFAULT_CHAT_PROMPT_FALLBACK
    return normalized


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

import base64
import logging
import mimetypes
import os
from urllib.parse import urlparse

import requests
from fastapi import HTTPException, status

from app.core.config import settings
from app.models.message import Message

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
logger = logging.getLogger(__name__)


def build_system_prompt(input_language: str, output_language: str, default_prompt: str = "") -> str:
    language_hint = input_language if input_language and input_language != "auto" else "unknown"
    base_prompt = (
        "You are Garo2, a careful multilingual AI assistant for English and Garo. "
        f"The client-provided input language hint is {language_hint}. "
        "Do not blindly trust that hint. Detect the actual user language from the message content. "
        f"Always answer fully in {output_language}. "
        "Never switch languages unless the user explicitly asks for it. "
        "If the requested output language is Garo, write natural, fluent Garo instead of a word-for-word translation. "
        "Avoid unnecessary English, Hindi, or Bengali words in Garo answers except for proper nouns, quoted text, or technical terms that should stay unchanged. "
        "If the requested output language is English, write natural, clear English. "
        "Preserve names, numbers, dates, and factual details accurately. "
        "If you are unsure about a Garo phrasing, choose simple natural wording and avoid inventing facts."
    )
    custom_prompt = default_prompt.strip()
    if custom_prompt:
        base_prompt = f"{base_prompt}\n\nAdditional admin instructions:\n{custom_prompt}"
    return base_prompt


def serialize_messages(messages: list[Message], input_language: str, output_language: str, default_prompt: str = "") -> list[dict]:
    serialized: list[dict] = [{"role": "system", "content": build_system_prompt(input_language, output_language, default_prompt)}]
    for message in messages:
        if message.image_url:
            serialized.append(
                {
                    "role": message.role,
                    "content": [
                        {"type": "text", "text": message.content},
                        {"type": "image_url", "image_url": {"url": resolve_image_payload(message.image_url)}},
                    ],
                }
            )
        else:
            serialized.append({"role": message.role, "content": message.content})
    return serialized


def resolve_image_payload(image_url: str) -> str:
    parsed = urlparse(image_url)
    if parsed.path.startswith("/uploads/"):
        filename = os.path.basename(parsed.path)
        absolute_path = os.path.join(settings.upload_dir_path, filename)
        mime_type = mimetypes.guess_type(absolute_path)[0] or "image/jpeg"
        with open(absolute_path, "rb") as image_file:
            encoded = base64.b64encode(image_file.read()).decode("utf-8")
        return f"data:{mime_type};base64,{encoded}"
    return image_url


def generate_ai_response(
    messages: list[Message],
    input_language: str,
    output_language: str,
    model: str | None = None,
    default_prompt: str = "",
) -> str:
    has_image = any(message.image_url for message in messages)
    resolved_model = model or (settings.openrouter_vision_model if has_image else settings.openrouter_text_model)
    payload = {
        "model": resolved_model,
        "messages": serialize_messages(messages, input_language, output_language, default_prompt),
    }
    headers = {
        "Authorization": f"Bearer {settings.openrouter_api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": settings.openrouter_site_url,
        "X-Title": settings.openrouter_site_name,
    }

    response = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=90)
    if response.status_code >= 400:
        try:
            detail = response.json().get("error", {}).get("message", "OpenRouter request failed")
        except ValueError:
            detail = response.text or "OpenRouter request failed"
        logger.error(
            "OpenRouter request failed with %s for model %s: %s",
            response.status_code,
            resolved_model,
            detail,
        )
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=detail)

    data = response.json()
    choices = data.get("choices") or []
    if not choices:
        logger.error("OpenRouter returned no choices for model %s", resolved_model)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="OpenRouter returned no choices")
    return choices[0]["message"]["content"].strip()

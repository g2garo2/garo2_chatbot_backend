import base64
import logging
import mimetypes
import os
from urllib.parse import urlparse

import requests
from fastapi import HTTPException, status

from app.core.config import settings
from app.models.message import Message

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
logger = logging.getLogger(__name__)


def _resolve_image_data(image_url: str) -> tuple[str, str]:
    parsed = urlparse(image_url)
    if parsed.path.startswith("/uploads/"):
        filename = os.path.basename(parsed.path)
        absolute_path = os.path.join(settings.upload_dir_path, filename)
        mime_type = mimetypes.guess_type(absolute_path)[0] or "image/jpeg"
        with open(absolute_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode("utf-8"), mime_type

    response = requests.get(image_url, timeout=60)
    response.raise_for_status()
    mime_type = response.headers.get("Content-Type", "image/jpeg").split(";")[0]
    return base64.b64encode(response.content).decode("utf-8"), mime_type


def _post_generate_content(model: str, payload: dict) -> dict:
    if not settings.gemini_api_key:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Gemini API key is not configured")

    url = f"{GEMINI_API_BASE}/{model}:generateContent?key={settings.gemini_api_key}"
    response = requests.post(url, json=payload, timeout=120)
    if response.status_code >= 400:
        try:
            detail = response.json().get("error", {}).get("message", "Gemini request failed")
        except ValueError:
            detail = response.text or "Gemini request failed"
        logger.error("Gemini request failed with %s for model %s: %s", response.status_code, model, detail)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=detail)
    return response.json()


def _extract_text(data: dict) -> str:
    candidates = data.get("candidates") or []
    for candidate in candidates:
        parts = (((candidate.get("content") or {}).get("parts")) or [])
        text_chunks = [part.get("text", "") for part in parts if part.get("text")]
        if text_chunks:
            return "\n".join(text_chunks).strip()
    logger.error("Gemini returned no text response for model output")
    raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Gemini returned no text response")


def _extract_image(data: dict) -> tuple[str | None, str | None, str | None]:
    candidates = data.get("candidates") or []
    text_chunks: list[str] = []
    for candidate in candidates:
        parts = (((candidate.get("content") or {}).get("parts")) or [])
        for part in parts:
            if part.get("text"):
                text_chunks.append(part["text"])
            inline_data = part.get("inlineData") or part.get("inline_data")
            if inline_data and inline_data.get("data"):
                return (
                    inline_data.get("data"),
                    inline_data.get("mimeType") or inline_data.get("mime_type"),
                    "\n".join(text_chunks).strip() or None,
                )
    return None, None, "\n".join(text_chunks).strip() or None


def build_chat_prompt(input_language: str, output_language: str, default_prompt: str = "") -> str:
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


def generate_chat_response(messages: list[Message], input_language: str, output_language: str, default_prompt: str = "") -> str:
    contents = [{"role": "user", "parts": [{"text": build_chat_prompt(input_language, output_language, default_prompt)}]}]
    for message in messages:
        parts: list[dict] = [{"text": message.content}]
        if message.image_url:
            image_data, mime_type = _resolve_image_data(message.image_url)
            parts.append({"inline_data": {"mime_type": mime_type, "data": image_data}})
        contents.append({"role": "model" if message.role == "assistant" else "user", "parts": parts})

    data = _post_generate_content(settings.gemini_text_model, {"contents": contents})
    return _extract_text(data)


def translate_text(text: str, source_language: str, target_language: str) -> str:
    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {
                        "text": (
                            "You are a precise translator between English and Garo. "
                            f"Translate the following text from {source_language} to {target_language}. "
                            "Preserve the original meaning, tone, names, numbers, and formatting. "
                            "Do not explain the translation. Do not add notes, headings, or quotation marks. "
                            "If the target language is Garo, use natural fluent Garo instead of a literal word-for-word translation. "
                            "Keep proper nouns and technical terms unchanged when they should remain unchanged. "
                            "Return only the translated text.\n\n"
                            f"{text}"
                        )
                    }
                ],
            }
        ]
    }
    data = _post_generate_content(settings.gemini_text_model, payload)
    return _extract_text(data)


def analyze_image(image_url: str, prompt: str, output_language: str) -> str:
    image_data, mime_type = _resolve_image_data(image_url)
    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {"text": f"{prompt}\nRespond in {output_language}."},
                    {"inline_data": {"mime_type": mime_type, "data": image_data}},
                ],
            }
        ]
    }
    data = _post_generate_content(settings.gemini_image_model, payload)
    return _extract_text(data)


def generate_image(prompt: str) -> tuple[str | None, str | None, str | None]:
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"responseModalities": ["TEXT", "IMAGE"]},
    }
    data = _post_generate_content(settings.gemini_image_model, payload)
    return _extract_image(data)

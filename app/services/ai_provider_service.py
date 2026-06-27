from app.core.config import settings
from app.core.plans import FREE_PLAN, get_plan_config
from app.models.message import Message
from app.models.user import User
from app.services.gemini_service import analyze_image, generate_chat_response, generate_image, translate_text
from app.services.openrouter_service import generate_ai_response


def generate_chat_for_user(user: User, messages: list[Message], input_language: str, output_language: str) -> str:
    plan = get_plan_config(user.plan)
    has_image = any(message.image_url for message in messages)
    if plan.key == FREE_PLAN and not has_image:
        return generate_ai_response(
            messages=messages,
            input_language=input_language,
            output_language=output_language,
            model=settings.openrouter_free_model,
        )
    return generate_chat_response(messages=messages, input_language=input_language, output_language=output_language)


def translate_for_user(user: User, text: str, source_language: str, target_language: str) -> str:
    _ = get_plan_config(user.plan)
    return translate_text(text=text, source_language=source_language, target_language=target_language)


def analyze_image_for_user(user: User, image_url: str, prompt: str, output_language: str) -> str:
    _ = get_plan_config(user.plan)
    return analyze_image(image_url=image_url, prompt=prompt, output_language=output_language)


def generate_image_for_user(user: User, prompt: str) -> tuple[str | None, str | None, str | None]:
    _ = get_plan_config(user.plan)
    return generate_image(prompt=prompt)

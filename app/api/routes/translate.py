from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.translate import TranslateRequest, TranslateResponse
from app.services.ai_provider_service import translate_for_user
from app.services.usage_service import enforce_translation_limit, increment_translation_usage

router = APIRouter()


@router.post("/", response_model=TranslateResponse)
def translate_text_endpoint(
    payload: TranslateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TranslateResponse:
    if not payload.text.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Text is required")

    enforce_translation_limit(db, current_user)
    translated_text = translate_for_user(
        user=current_user,
        text=payload.text.strip(),
        source_language=payload.source_language,
        target_language=payload.target_language,
    )
    increment_translation_usage(db, current_user)
    db.commit()
    return TranslateResponse(translated_text=translated_text)

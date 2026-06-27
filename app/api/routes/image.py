from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.image import ImageAnalyzeRequest, ImageAnalyzeResponse, ImageGenerateRequest, ImageGenerateResponse
from app.services.ai_provider_service import analyze_image_for_user, generate_image_for_user
from app.services.usage_service import enforce_image_generation_limit, increment_image_generation_usage

router = APIRouter()


@router.post("/analyze", response_model=ImageAnalyzeResponse)
def analyze_image_endpoint(
    payload: ImageAnalyzeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ImageAnalyzeResponse:
    if not payload.image_url.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Image URL is required")

    content = analyze_image_for_user(
        user=current_user,
        image_url=payload.image_url.strip(),
        prompt=payload.prompt.strip() or "Please analyze this image.",
        output_language=payload.output_language,
    )
    return ImageAnalyzeResponse(content=content)


@router.post("/generate", response_model=ImageGenerateResponse)
def generate_image_endpoint(
    payload: ImageGenerateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ImageGenerateResponse:
    if not payload.prompt.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Prompt is required")

    enforce_image_generation_limit(db, current_user)
    image_base64, mime_type, text = generate_image_for_user(current_user, payload.prompt.strip())
    increment_image_generation_usage(db, current_user)
    db.commit()
    return ImageGenerateResponse(image_base64=image_base64, mime_type=mime_type, text=text)

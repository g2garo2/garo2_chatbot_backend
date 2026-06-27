import os
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.db.session import get_db
from app.models.user import User
from app.services.usage_service import enforce_image_upload_limit, increment_image_upload_usage

router = APIRouter()

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}


@router.post("/image")
def upload_image(
    image: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    enforce_image_upload_limit(db, current_user)
    if image.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported image type")

    raw = image.file.read()
    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    if len(raw) > max_bytes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Image too large")

    suffix = Path(image.filename or "upload.jpg").suffix or ".jpg"
    filename = f"{current_user.id}_{uuid4().hex}{suffix}"
    destination = os.path.join(settings.upload_dir_path, filename)
    with open(destination, "wb") as file_obj:
        file_obj.write(raw)

    increment_image_upload_usage(db, current_user)
    db.commit()
    return {"image_url": f"{settings.backend_base_url}/uploads/{filename}"}

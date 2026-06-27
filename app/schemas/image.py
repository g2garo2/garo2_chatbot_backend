from pydantic import BaseModel


class ImageAnalyzeRequest(BaseModel):
    image_url: str
    prompt: str = "Please analyze this image."
    output_language: str = "english"


class ImageAnalyzeResponse(BaseModel):
    content: str


class ImageGenerateRequest(BaseModel):
    prompt: str


class ImageGenerateResponse(BaseModel):
    image_base64: str | None = None
    mime_type: str | None = None
    text: str | None = None

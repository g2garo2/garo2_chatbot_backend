from pydantic import BaseModel


class TranslateRequest(BaseModel):
    text: str
    source_language: str = "auto"
    target_language: str = "english"


class TranslateResponse(BaseModel):
    translated_text: str

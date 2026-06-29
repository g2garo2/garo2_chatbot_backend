import os
from functools import cached_property
from urllib.parse import quote_plus

from dotenv import load_dotenv
from pydantic import Field
from pydantic import field_validator
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join(BASE_DIR, ".env"))


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    app_name: str = Field(default="Garo2 API", alias="APP_NAME")
    app_env: str = Field(default="development", alias="APP_ENV")
    app_debug: bool = Field(default=True, alias="APP_DEBUG")
    api_v1_prefix: str = Field(default="/api", alias="API_V1_PREFIX")
    secret_key: str = Field(alias="SECRET_KEY")
    access_token_expire_minutes: int = Field(default=10080, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    admin_username: str = Field(default="admin", alias="ADMIN_USERNAME")
    admin_password: str = Field(default="change-me-now", alias="ADMIN_PASSWORD")

    mysql_host: str = Field(alias="MYSQL_HOST")
    mysql_port: int = Field(default=3306, alias="MYSQL_PORT")
    mysql_user: str = Field(alias="MYSQL_USER")
    mysql_password: str = Field(alias="MYSQL_PASSWORD")
    mysql_database: str = Field(alias="MYSQL_DATABASE")

    google_client_id: str = Field(alias="GOOGLE_CLIENT_ID")
    openrouter_api_key: str = Field(alias="OPENROUTER_API_KEY")
    openrouter_text_model: str = Field(default="openai/gpt-4o-mini", alias="OPENROUTER_TEXT_MODEL")
    openrouter_free_model: str = Field(default="openai/gpt-4o-mini", alias="OPENROUTER_FREE_MODEL")
    openrouter_vision_model: str = Field(default="openai/gpt-4.1-mini", alias="OPENROUTER_VISION_MODEL")
    openrouter_site_url: str = Field(default="https://garo2.com", alias="OPENROUTER_SITE_URL")
    openrouter_site_name: str = Field(default="Garo2", alias="OPENROUTER_SITE_NAME")
    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")
    gemini_text_model: str = Field(default="gemini-3.5-flash", alias="GEMINI_TEXT_MODEL")
    gemini_image_model: str = Field(default="gemini-2.5-flash-image-preview", alias="GEMINI_IMAGE_MODEL")
    razorpay_key_id: str = Field(default="", alias="RAZORPAY_KEY_ID")
    razorpay_key_secret: str = Field(default="", alias="RAZORPAY_KEY_SECRET")
    razorpay_plan_plus: str = Field(default="", alias="RAZORPAY_PLAN_PLUS")
    razorpay_plan_pro: str = Field(default="", alias="RAZORPAY_PLAN_PRO")
    razorpay_plan_ultra: str = Field(default="", alias="RAZORPAY_PLAN_ULTRA")
    razorpay_webhook_secret: str = Field(default="", alias="RAZORPAY_WEBHOOK_SECRET")

    backend_base_url: str = Field(default="http://127.0.0.1:8000", alias="BACKEND_BASE_URL")
    upload_dir: str = Field(default="uploads", alias="UPLOAD_DIR")
    max_upload_size_mb: int = Field(default=10, alias="MAX_UPLOAD_SIZE_MB")
    cors_origins_raw: str = Field(default="http://localhost:5173", alias="CORS_ORIGINS")

    jwt_algorithm: str = "HS256"

    @model_validator(mode="after")
    def validate_production_settings(self) -> "Settings":
        normalized_env = self.app_env.strip().lower()
        is_production = normalized_env == "production"

        if is_production and self.app_debug:
            raise ValueError("APP_DEBUG must be false when APP_ENV=production")
        if is_production and self.secret_key == "change-me-to-a-long-random-string":
            raise ValueError("SECRET_KEY must be changed before production deployment")
        if is_production and self.admin_password == "change-me-now":
            raise ValueError("ADMIN_PASSWORD must be changed before production deployment")
        if is_production and self.backend_base_url.startswith(("http://127.0.0.1", "http://localhost")):
            raise ValueError("BACKEND_BASE_URL must be a public production URL when APP_ENV=production")

        return self

    @field_validator(
        "openrouter_text_model",
        "openrouter_free_model",
        "openrouter_vision_model",
        "gemini_text_model",
        "gemini_image_model",
        mode="before",
    )
    @classmethod
    def normalize_model_name(cls, value: str) -> str:
        if not isinstance(value, str):
            return value

        normalized = value.strip()
        if len(normalized) >= 2 and normalized[0] == normalized[-1] and normalized[0] in {'"', "'"}:
            normalized = normalized[1:-1].strip()
        return normalized

    @cached_property
    def database_url(self) -> str:
        quoted_user = quote_plus(self.mysql_user)
        quoted_password = quote_plus(self.mysql_password)
        return (
            f"mysql+pymysql://{quoted_user}:{quoted_password}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}"
        )

    @cached_property
    def upload_dir_path(self) -> str:
        return os.path.join(BASE_DIR, self.upload_dir)

    @cached_property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins_raw.split(",") if origin.strip()]


settings = Settings()
os.makedirs(settings.upload_dir_path, exist_ok=True)

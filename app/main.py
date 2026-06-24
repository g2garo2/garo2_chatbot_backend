from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes import auth, chat, health, upload
from app.core.config import settings
from app.core.exceptions import register_exception_handlers

app = FastAPI(
    title=settings.app_name,
    debug=settings.app_debug,
    docs_url="/docs" if settings.app_debug else None,
    redoc_url="/redoc" if settings.app_debug else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)

app.include_router(health.router, prefix=settings.api_v1_prefix, tags=["Health"])
app.include_router(auth.router, prefix=f"{settings.api_v1_prefix}/auth", tags=["Auth"])
app.include_router(chat.router, prefix=f"{settings.api_v1_prefix}/chat", tags=["Chat"])
app.include_router(upload.router, prefix=f"{settings.api_v1_prefix}/upload", tags=["Upload"])

app.mount("/uploads", StaticFiles(directory=settings.upload_dir_path), name="uploads")

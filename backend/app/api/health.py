"""Liveness endpoint that does not load ML models."""

from fastapi import APIRouter

from backend.app.core.config import settings
from backend.app.models.schemas import HealthResponse


router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health() -> dict:
    return {
        "status": "ok",
        "service": settings.app_name,
        "llm_configured": bool(settings.llm_api_key),
        "embedding_model": settings.embedding_model,
    }

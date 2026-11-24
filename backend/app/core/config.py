"""Central application configuration loaded from the project .env file."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(PROJECT_ROOT / ".env")


def _csv_setting(name: str, default: str) -> list[str]:
    return [value.strip() for value in os.getenv(name, default).split(",") if value.strip()]


class Settings:
    app_name = os.getenv("APP_NAME", "RetrivAI")
    environment = os.getenv("APP_ENV", "development")
    debug = os.getenv("APP_DEBUG", "false").lower() in {"1", "true", "yes"}
    database_url = os.getenv("DATABASE_URL", "")
    embedding_dimension = int(os.getenv("EMBEDDING_DIMENSION", "768"))
    embedding_model = os.getenv(
        "EMBEDDING_MODEL", "sentence-transformers/all-mpnet-base-v2"
    )
    reranker_model = os.getenv(
        "RERANKER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2"
    )
    reranker_enabled = os.getenv("RERANKER_ENABLED", "true").lower() in {
        "1", "true", "yes"
    }
    llm_api_key = os.getenv("LLM_API_KEY", "").strip()
    llm_base_url = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    llm_model = os.getenv("LLM_MODEL", "gpt-4o-mini").strip()
    llm_timeout_seconds = float(os.getenv("LLM_TIMEOUT_SECONDS", "45"))
    llm_reasoning_effort = os.getenv("LLM_REASONING_EFFORT", "").strip()
    allowed_origins = _csv_setting(
        "FRONTEND_URLS", "http://localhost:3000,http://127.0.0.1:3000"
    )
    max_upload_bytes = int(os.getenv("MAX_UPLOAD_MB", "20")) * 1024 * 1024
    chunk_size = int(os.getenv("CHUNK_SIZE", "1000"))
    chunk_overlap = int(os.getenv("CHUNK_OVERLAP", "200"))
    default_top_k = int(os.getenv("DEFAULT_TOP_K", "5"))
    max_top_k = int(os.getenv("MAX_TOP_K", "20"))
    max_context_chars = int(os.getenv("MAX_CONTEXT_CHARS", "14000"))
    min_relevance_score = float(os.getenv("MIN_RELEVANCE_SCORE", "0.22"))
    auth_cookie_name = os.getenv("AUTH_COOKIE_NAME", "retrivai_session")
    auth_token_days = int(os.getenv("AUTH_TOKEN_DAYS", "7"))
    cookie_secure = os.getenv("COOKIE_SECURE", "false").lower() in {
        "1", "true", "yes"
    }
    cookie_samesite = os.getenv("COOKIE_SAMESITE", "lax").lower()
    rate_limit_per_minute = int(os.getenv("RATE_LIMIT_PER_MINUTE", "90"))


settings = Settings()

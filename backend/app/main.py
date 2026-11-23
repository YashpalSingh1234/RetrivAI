"""FastAPI application entry point."""

from __future__ import annotations

import logging
import re
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.app.api import auth, documents, evaluation, health, query
from backend.app.core.config import settings
from backend.app.core.database import initialize_database


logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("retrivai")

app = FastAPI(
    title=settings.app_name,
    description="A document-grounded assistant with semantic search and source citations.",
    version="1.0.0",
    docs_url="/docs" if settings.environment != "production" else None,
    redoc_url="/redoc" if settings.environment != "production" else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Request-ID"],
)


@app.middleware("http")
async def request_observability(request: Request, call_next):
    supplied_id = request.headers.get("X-Request-ID", "")
    request_id = supplied_id if re.fullmatch(r"[A-Za-z0-9._-]{1,80}", supplied_id) else str(uuid.uuid4())
    request.state.request_id = request_id
    started = time.perf_counter()
    try:
        if request.method == "POST" and request.url.path == "/documents/upload":
            raw_length = request.headers.get("Content-Length")
            if raw_length and raw_length.isdigit() and int(raw_length) > settings.max_upload_bytes + 1024 * 1024:
                response = JSONResponse(status_code=413, content={"detail": "The upload is larger than the allowed limit."})
                response.headers["X-Request-ID"] = request_id
                return response
        if (
            request.method in {"POST", "PUT", "PATCH", "DELETE"}
            and request.cookies.get(settings.auth_cookie_name)
            and not request.headers.get("Authorization", "").lower().startswith("bearer ")
            and request.headers.get("Origin") not in settings.allowed_origins
        ):
            response = JSONResponse(
                status_code=403,
                content={"detail": "Request origin is not allowed."},
            )
            response.headers["X-Request-ID"] = request_id
            return response
        response = await call_next(request)
    except Exception:
        logger.exception("request failed id=%s method=%s path=%s", request_id, request.method, request.url.path)
        response = JSONResponse(status_code=500, content={"detail": "An unexpected server error occurred."})
    elapsed_ms = round((time.perf_counter() - started) * 1000)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Response-Time-ms"] = str(elapsed_ms)
    logger.info(
        "request id=%s method=%s path=%s status=%s duration_ms=%s",
        request_id, request.method, request.url.path, response.status_code, elapsed_ms,
    )
    return response


@app.on_event("startup")
def startup() -> None:
    initialize_database()


@app.get("/", include_in_schema=False)
def root() -> dict[str, str]:
    return {"service": settings.app_name, "health": "/health", "api_docs": "/docs"}


app.include_router(health.router)
app.include_router(auth.router)
app.include_router(documents.router)
app.include_router(query.router)
app.include_router(evaluation.router)

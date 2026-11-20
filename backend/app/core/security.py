"""Input validation and small in-process rate limiter for the local API."""

from __future__ import annotations

import re
import time
from collections import defaultdict, deque
from io import BytesIO
from pathlib import PurePath
from zipfile import BadZipFile, ZipFile

from fastapi import HTTPException, Request, status

from backend.app.core.config import settings


SUPPORTED_TYPES = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".txt": "text/plain",
}


def safe_filename(filename: str | None) -> str:
    name = PurePath((filename or "").replace("\\", "/")).name
    name = re.sub(r"[^\w.() -]", "_", name, flags=re.UNICODE).strip(" .")
    if not name:
        raise HTTPException(status_code=400, detail="A valid filename is required.")
    return name[:180]


def validate_uploaded_file(
    filename: str | None,
    content: bytes,
    declared_content_type: str | None = None,
) -> tuple[str, str]:
    name = safe_filename(filename)
    extension = PurePath(name).suffix.lower()
    if extension not in SUPPORTED_TYPES:
        raise HTTPException(
            status_code=415,
            detail="Unsupported file type. Upload a PDF, DOCX, or TXT document.",
        )
    declared = (declared_content_type or "").split(";", 1)[0].strip().lower()
    expected_type = SUPPORTED_TYPES[extension]
    allowed_declared_types = {
        expected_type,
        "application/octet-stream",
        "binary/octet-stream",
    }
    if extension == ".pdf":
        allowed_declared_types.add("application/x-pdf")
    elif extension == ".docx":
        allowed_declared_types.add("application/zip")
    if declared and declared not in allowed_declared_types:
        raise HTTPException(status_code=415, detail="The filename and declared file type do not match.")
    if not content:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")
    if len(content) > settings.max_upload_bytes:
        limit_mb = settings.max_upload_bytes // (1024 * 1024)
        raise HTTPException(status_code=413, detail=f"Files must be {limit_mb} MB or smaller.")

    if extension == ".pdf":
        if b"%PDF-" not in content[:1024]:
            raise HTTPException(status_code=415, detail="The file does not contain a valid PDF header.")
    elif extension == ".docx":
        if not content.startswith(b"PK"):
            raise HTTPException(status_code=415, detail="The file does not look like a DOCX archive.")
        try:
            with ZipFile(BytesIO(content)) as archive:
                entries = archive.infolist()
                names = {entry.filename for entry in entries}
                if "[Content_Types].xml" not in names or "word/document.xml" not in names:
                    raise HTTPException(status_code=415, detail="The DOCX document is missing required content.")
                expanded_size = sum(entry.file_size for entry in entries)
                if len(entries) > 1000 or expanded_size > settings.max_upload_bytes * 10:
                    raise HTTPException(status_code=413, detail="The DOCX archive expands beyond the allowed processing limit.")
        except BadZipFile as exc:
            raise HTTPException(status_code=415, detail="The DOCX archive is corrupt.") from exc
    else:
        try:
            content.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise HTTPException(status_code=415, detail="TXT files must use UTF-8 encoding.") from exc

    # MIME metadata is checked when supplied, then the file signature is verified.
    return name, expected_type


class InMemoryRateLimiter:
    """Fixed-window request limiter; suitable for a single-process demo deployment."""

    def __init__(self) -> None:
        self._requests: dict[str, deque[float]] = defaultdict(deque)

    def check(self, request: Request) -> None:
        now = time.monotonic()
        key = f"{request.client.host if request.client else 'unknown'}:{request.url.path}"
        events = self._requests[key]
        while events and now - events[0] > 60:
            events.popleft()
        limit = 10 if request.url.path.endswith(("/login", "/register")) else settings.rate_limit_per_minute
        if len(events) >= limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Please wait a minute and try again.",
                headers={"Retry-After": "60"},
            )
        events.append(now)


rate_limiter = InMemoryRateLimiter()

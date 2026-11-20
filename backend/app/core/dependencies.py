"""Common request dependencies for rate limiting and user authentication."""

from __future__ import annotations

from fastapi import Depends, Header, HTTPException, Request, status

from backend.app.core.auth import read_session
from backend.app.core.auth import get_user as lookup_user
from backend.app.core.config import settings
from backend.app.core.security import rate_limiter


def check_rate_limit(request: Request) -> None:
    rate_limiter.check(request)


def get_current_user(
    request: Request,
    authorization: str | None = Header(default=None),
) -> dict[str, str]:
    token = request.cookies.get(settings.auth_cookie_name)
    if not token and authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()
    user_id = read_session(token) if token else None
    user = lookup_user(user_id) if user_id else None
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sign in to continue.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


CurrentUser = dict[str, str]
AuthenticatedUser = Depends(get_current_user)

"""Registration, sign-in, and session endpoints."""

from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from backend.app.core.auth import authenticate_user, create_user, issue_session
from backend.app.core.config import settings
from backend.app.core.dependencies import check_rate_limit, get_current_user
from backend.app.models.schemas import AuthRequest, UserResponse


router = APIRouter(prefix="/auth", tags=["authentication"], dependencies=[Depends(check_rate_limit)])


def _set_session(response: Response, user_id: str) -> None:
    max_age = settings.auth_token_days * 24 * 60 * 60
    response.set_cookie(
        key=settings.auth_cookie_name,
        value=issue_session(user_id, max_age),
        max_age=max_age,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        path="/",
    )


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(payload: AuthRequest, response: Response) -> dict:
    try:
        user = create_user(payload.email, payload.password)
    except sqlite3.IntegrityError as exc:
        raise HTTPException(status_code=409, detail="An account with this email already exists.") from exc
    _set_session(response, user["id"])
    return user


@router.post("/login", response_model=UserResponse)
def login(payload: AuthRequest, response: Response) -> dict:
    user = authenticate_user(payload.email, payload.password)
    if user is None:
        raise HTTPException(status_code=401, detail="Email or password is incorrect.")
    _set_session(response, user["id"])
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response) -> Response:
    response.delete_cookie(
        key=settings.auth_cookie_name,
        secure=settings.cookie_secure,
        httponly=True,
        samesite=settings.cookie_samesite,
        path="/",
    )
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.get("/me", response_model=UserResponse)
def me(user: dict = Depends(get_current_user)) -> dict:
    return user

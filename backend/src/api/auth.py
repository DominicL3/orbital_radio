"""Spotify OAuth and session endpoints."""

from secrets import compare_digest
from typing import Any

from fastapi import APIRouter, Cookie, HTTPException, Query, Response, status
from pydantic import BaseModel

from src.config import get_settings
from src.services.auth_service import AuthService, session_manager

router = APIRouter(prefix="/auth", tags=["auth"])
auth_service: AuthService | None = None
SESSION_COOKIE = "orbital_session"
OAUTH_STATE_COOKIE = "orbital_oauth_state"


def _get_auth_service() -> AuthService:
    """Lazily create the configured Spotify client for an auth request."""
    global auth_service
    if auth_service is None:
        auth_service = AuthService(manager=session_manager)
    return auth_service


class AuthorizationResponse(BaseModel):
    """Authorization URL returned to the browser."""

    authorization_url: str


class CallbackResponse(BaseModel):
    """Safe metadata returned after successful OAuth."""

    session_active: bool
    user: dict[str, Any]


class MessageResponse(BaseModel):
    """Simple operation result."""

    message: str


def _safe_profile(profile: dict[str, Any]) -> dict[str, Any]:
    """Select non-sensitive profile metadata for the response."""
    return {
        key: profile[key]
        for key in ("id", "display_name", "country", "product")
        if key in profile
    }


def _set_cookie(response: Response, session_id: str) -> None:
    """Set the opaque server-side session cookie."""
    response.set_cookie(
        SESSION_COOKIE,
        session_id,
        httponly=True,
        secure=get_settings().environment == "production",
        samesite="lax",
        max_age=get_settings().session_expire_hours * 3600,
        path="/",
    )


def _set_state_cookie(response: Response, state: str) -> None:
    """Bind OAuth state to the initiating browser for ten minutes."""
    response.set_cookie(
        OAUTH_STATE_COOKIE,
        state,
        httponly=True,
        secure=get_settings().environment == "production",
        samesite="lax",
        max_age=get_settings().oauth_state_minutes * 60,
        path="/auth/spotify",
    )


@router.post("/spotify/login", response_model=AuthorizationResponse)
def spotify_login(response: Response) -> AuthorizationResponse:
    """Start Spotify OAuth."""
    try:
        service = _get_auth_service()
        authorization_url, state = service.create_authorization_request()
        result = AuthorizationResponse(authorization_url=authorization_url)
        _set_state_cookie(response, state)
        return result
    except ValueError as exc:
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR, "OAuth is not configured"
        ) from exc


@router.get("/spotify/callback", response_model=CallbackResponse)
def spotify_callback(
    response: Response,
    code: str | None = Query(default=None, min_length=1),
    state: str | None = Query(default=None, min_length=1),
    error: str | None = Query(default=None, max_length=100),
    state_cookie: str | None = Cookie(default=None, alias=OAUTH_STATE_COOKIE),
) -> CallbackResponse:
    """Complete Spotify's query-parameter OAuth callback."""
    try:
        state_matches = bool(
            state and state_cookie and compare_digest(state, state_cookie)
        )
    except TypeError:
        state_matches = False
    if error or not code or not state or not state_matches:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid OAuth callback")
    try:
        session_id, profile = _get_auth_service().complete_callback(code, state)
    except ValueError as exc:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Invalid OAuth callback"
        ) from exc
    except (RuntimeError, ConnectionError) as exc:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY, "Spotify authentication failed"
        ) from exc
    _set_cookie(response, session_id)
    response.delete_cookie(OAUTH_STATE_COOKIE, path="/auth/spotify")
    return CallbackResponse(session_active=True, user=_safe_profile(profile))


@router.post("/refresh", response_model=MessageResponse)
def refresh(
    session_id: str | None = Cookie(default=None, alias=SESSION_COOKIE),
) -> MessageResponse:
    """Refresh the current session's Spotify access token."""
    if not session_id:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Authentication required")
    try:
        _get_auth_service().refresh_access_token(session_id)
        return MessageResponse(message="Session refreshed")
    except (ValueError, RuntimeError, ConnectionError) as exc:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "Authentication required"
        ) from exc


@router.delete("/logout", response_model=MessageResponse)
def logout(
    response: Response,
    session_id: str | None = Cookie(default=None, alias=SESSION_COOKIE),
) -> MessageResponse:
    """Delete the current session and clear its cookie."""
    if session_id:
        if auth_service is not None:
            auth_service.logout_user(session_id)
    response.delete_cookie(SESSION_COOKIE, path="/")
    return MessageResponse(message="Logged out")

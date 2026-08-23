"""Unit tests for authentication orchestration."""

from datetime import timedelta
from unittest.mock import Mock

import pytest

from src.config import utcnow
from src.services.auth_service import AuthService
from src.services.session_manager import SessionManager


def service() -> AuthService:
    """Create an isolated service with mocked Spotify calls."""
    spotify = Mock()
    result = AuthService(spotify)
    result.session_manager = SessionManager()
    return result


def test_state_and_callback_lifecycle() -> None:
    """A state is consumed once and creates a server-side session."""
    auth = service()
    auth.spotify_client.authenticate_user.return_value = {
        "access_token": "access",
        "refresh_token": "refresh",
        "expires_in": 60,
    }
    auth.spotify_client.get_user_profile.return_value = {"id": "user"}
    state = auth.session_manager.create_state()
    session_id, profile = auth.complete_callback("code", state)
    assert auth.validate_session(session_id)
    assert profile == {"id": "user"}
    with pytest.raises(ValueError, match="state"):
        auth.complete_callback("code", state)


def test_refresh_converts_expiry_and_preserves_refresh_token() -> None:
    """Refresh updates access expiry while retaining Spotify's refresh token."""
    auth = service()
    auth.spotify_client.refresh_user_token.return_value = {
        "access_token": "new",
        "expires_in": 3600,
    }
    session_id = auth.session_manager.create_session(
        {
            "spotify_tokens": {"refresh_token": "old", "access_token": "old"},
            "expires_at": utcnow() + timedelta(hours=1),
        }
    )
    tokens = auth.refresh_access_token(session_id)
    assert tokens["access_token"] == "new"
    assert tokens["refresh_token"] == "old"
    assert tokens["expires_at"] > utcnow()


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"access_token": "access", "refresh_token": "refresh"},
        {"access_token": "access", "refresh_token": "refresh", "expires_in": 0},
        {"access_token": "access", "refresh_token": "refresh", "expires_in": "3600"},
    ],
)
def test_malformed_exchange_payload_is_rejected(payload: dict[str, object]) -> None:
    """Reject token responses without complete, typed expiry data."""
    auth = service()
    auth.spotify_client.authenticate_user.return_value = payload
    with pytest.raises(ValueError):
        auth.exchange_code_for_tokens("code")


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"access_token": "new", "expires_in": 0},
        {"access_token": "new", "refresh_token": "", "expires_in": 3600},
    ],
)
def test_malformed_refresh_payload_is_rejected(payload: dict[str, object]) -> None:
    """Reject malformed refresh responses after preserving the old refresh token."""
    auth = service()
    auth.spotify_client.refresh_user_token.return_value = payload
    session_id = auth.session_manager.create_session(
        {
            "spotify_tokens": {"refresh_token": "old"},
            "expires_at": utcnow() + timedelta(hours=1),
        }
    )
    with pytest.raises(ValueError):
        auth.refresh_access_token(session_id)

"""Integration tests for the Spotify OAuth endpoints."""

from datetime import timedelta
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

import src.api.auth as auth_api
from src.config import utcnow
from src.main import app
from src.services.auth_service import AuthService
from src.services.session_manager import SessionManager


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """Create a client with isolated in-memory authentication state."""
    manager = SessionManager()
    spotify = Mock()
    spotify.get_authorization_url.side_effect = lambda state: (
        f"https://accounts.spotify.com/authorize?scope=user-read-private&state={state}"
    )
    spotify.authenticate_user.return_value = {
        "access_token": "access",
        "refresh_token": "refresh",
        "expires_in": 3600,
    }
    spotify.get_user_profile.return_value = {
        "id": "user-1",
        "display_name": "Test User",
        "country": "US",
    }
    spotify.refresh_user_token.return_value = {
        "access_token": "new-access",
        "expires_in": 3600,
    }
    monkeypatch.setattr(
        auth_api,
        "auth_service",
        AuthService(spotify_client=spotify, manager=manager),
    )
    return TestClient(app)


def test_login_creates_state_and_authorization_url(client: TestClient) -> None:
    """Login returns a Spotify URL containing a stored state."""
    result = client.post("/auth/spotify/login")
    assert result.status_code == 200
    assert "orbital_oauth_state=" in result.headers["set-cookie"]
    assert "HttpOnly" in result.headers["set-cookie"]
    assert "SameSite=lax" in result.headers["set-cookie"]
    assert "state=" in result.json()["authorization_url"]
    assert "scope=user-read-private" in result.json()["authorization_url"]


def test_callback_rejects_invalid_and_reused_state(client: TestClient) -> None:
    """OAuth state is required and single-use."""
    assert client.get("/auth/spotify/callback?code=code&state=bad").status_code == 400
    url = client.post("/auth/spotify/login").json()["authorization_url"]
    state = url.split("state=", 1)[1]
    assert (
        client.get("/auth/spotify/callback?code=code&state=%C3%A9").status_code == 400
    )
    client.cookies.delete("orbital_oauth_state")
    assert (
        client.get(f"/auth/spotify/callback?code=code&state={state}").status_code == 400
    )
    client.cookies.set("orbital_oauth_state", state, path="/auth/spotify")
    assert (
        client.get(f"/auth/spotify/callback?code=code&state={state}").status_code == 200
    )
    client.cookies.set("orbital_oauth_state", state, path="/auth/spotify")
    assert (
        client.get(f"/auth/spotify/callback?code=code&state={state}").status_code == 400
    )


def test_successful_callback_sets_cookie_without_tokens(client: TestClient) -> None:
    """Callback returns profile metadata and only an opaque cookie."""
    url = client.post("/auth/spotify/login").json()["authorization_url"]
    state = url.split("state=", 1)[1]
    result = client.get(f"/auth/spotify/callback?code=code&state={state}")
    assert result.status_code == 200
    assert "access" not in result.text and "refresh" not in result.text
    assert "orbital_session=" in result.headers["set-cookie"]
    assert 'orbital_oauth_state=""' in result.headers["set-cookie"]


def test_refresh_updates_session_without_returning_token(client: TestClient) -> None:
    """Refresh uses the cookie and keeps token material server-side."""
    url = client.post("/auth/spotify/login").json()["authorization_url"]
    state = url.split("state=", 1)[1]
    client.get(f"/auth/spotify/callback?code=code&state={state}")
    result = client.post("/auth/refresh")
    assert result.status_code == 200
    assert "access_token" not in result.text


def test_logout_clears_session_cookie(client: TestClient) -> None:
    """Logout deletes the session and clears the cookie."""
    result = client.delete("/auth/logout")
    assert result.status_code == 200
    assert "Max-Age=0" in result.headers["set-cookie"]


def test_expired_session_is_rejected(client: TestClient) -> None:
    """Expired sessions cannot refresh."""
    service = auth_api.auth_service
    assert service is not None
    session_id = service.session_manager.create_session(
        {
            "spotify_tokens": {"refresh_token": "refresh"},
            "expires_at": utcnow() - timedelta(seconds=1),
        }
    )
    client.cookies.set("orbital_session", session_id)
    assert client.post("/auth/refresh").status_code == 401

"""Authentication orchestration for Spotify OAuth and temporary sessions."""

from datetime import timedelta
from typing import Any

from src.config import get_settings, utcnow
from src.core.spotify_client import SpotifyClient
from src.services.session_manager import SessionManager

session_manager = SessionManager()


class AuthService:
    """Coordinate OAuth exchanges without exposing Spotify tokens to clients."""

    def __init__(
        self,
        spotify_client: SpotifyClient | None = None,
        manager: SessionManager | None = None,
    ) -> None:
        """Initialize Spotify client and in-memory session storage."""
        self.spotify_client = spotify_client or SpotifyClient()
        self.session_manager = manager or session_manager

    def get_authorization_url(self) -> str:
        """Create and persist OAuth state before returning Spotify's URL."""
        return self.create_authorization_request()[0]

    def create_authorization_request(self) -> tuple[str, str]:
        """Create an OAuth URL and return it with its server-side state."""
        state = self.session_manager.create_state()
        return self.spotify_client.get_authorization_url(state), state

    def exchange_code_for_tokens(self, code: str) -> dict[str, Any]:
        """Exchange an authorization code through the Spotify client."""
        tokens = self.spotify_client.authenticate_user(code)
        if not isinstance(tokens, dict):
            raise ValueError("Spotify returned an invalid token response")
        if (
            not isinstance(tokens.get("access_token"), str)
            or not tokens["access_token"]
        ):
            raise ValueError("Spotify returned no access token")
        if (
            not isinstance(tokens.get("refresh_token"), str)
            or not tokens["refresh_token"]
        ):
            raise ValueError("Spotify returned no refresh token")
        return self._with_expiry(tokens)

    def get_user_profile(self, access_token: str) -> dict[str, Any]:
        """Fetch a Spotify profile through the Spotify client."""
        return self.spotify_client.get_user_profile(access_token)

    def create_user_session(
        self, tokens: dict[str, Any], profile: dict[str, Any]
    ) -> str:
        """Create a server-side session and return its opaque identifier."""
        expires_at = utcnow() + timedelta(hours=get_settings().session_expire_hours)
        return self.session_manager.create_session(
            {
                "spotify_tokens": tokens,
                "user_profile": profile,
                "expires_at": expires_at,
            }
        )

    def complete_callback(self, code: str, state: str) -> tuple[str, dict[str, Any]]:
        """Validate OAuth state, exchange code, fetch profile, and create a session."""
        if not self.session_manager.consume_state(state):
            raise ValueError("Invalid or expired OAuth state")
        tokens = self.exchange_code_for_tokens(code)
        profile = self.get_user_profile(tokens["access_token"])
        return self.create_user_session(tokens, profile), profile

    def refresh_access_token(self, session_id: str) -> dict[str, Any]:
        """Refresh a session's Spotify token and persist the new expiry."""
        session = self.session_manager.get_session(session_id)
        if session is None:
            raise ValueError("Invalid or expired session")
        tokens = session["spotify_tokens"]
        refreshed = self.spotify_client.refresh_user_token(tokens["refresh_token"])
        if not isinstance(refreshed, dict):
            raise ValueError("Spotify returned an invalid token response")
        refreshed["refresh_token"] = refreshed.get(
            "refresh_token", tokens["refresh_token"]
        )
        session["spotify_tokens"] = self._with_expiry(refreshed)
        self.session_manager.update_session(session_id, session)
        return session["spotify_tokens"]

    def validate_session(self, session_id: str) -> bool:
        """Return whether a session is active."""
        return self.session_manager.get_session(session_id) is not None

    def logout_user(self, session_id: str) -> None:
        """Delete a session."""
        self.session_manager.delete_session(session_id)

    def cleanup_expired_sessions(self) -> None:
        """Remove expired temporary state."""
        self.session_manager.cleanup_expired()

    @staticmethod
    def _with_expiry(tokens: dict[str, Any]) -> dict[str, Any]:
        """Convert Spotify's relative expiry into a server-side UTC timestamp."""
        if not isinstance(tokens, dict):
            raise ValueError("Spotify returned an invalid token response")
        for name in ("access_token", "refresh_token"):
            if not isinstance(tokens.get(name), str) or not tokens[name]:
                raise ValueError(f"Spotify returned no {name}")
        expires_in = tokens.get("expires_in")
        if (
            not isinstance(expires_in, int)
            or isinstance(expires_in, bool)
            or expires_in <= 0
        ):
            raise ValueError("Spotify returned an invalid token expiry")
        result = dict(tokens)
        result["expires_at"] = utcnow() + timedelta(seconds=expires_in)
        return result

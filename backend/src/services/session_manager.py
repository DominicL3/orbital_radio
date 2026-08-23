"""Temporary in-memory storage for authentication sessions and OAuth state."""

from copy import deepcopy
from datetime import datetime, timedelta
from secrets import token_urlsafe
from threading import RLock
from typing import Any

from src.config import get_settings, utcnow


class SessionManager:
    """Store short-lived server-side sessions and one-time OAuth states."""

    def __init__(self, state_minutes: int | None = None) -> None:
        """Initialize empty session storage."""
        self.state_minutes = (
            state_minutes if state_minutes is not None else get_settings().oauth_state_minutes
        )
        self._sessions: dict[str, dict[str, Any]] = {}
        self._states: dict[str, datetime] = {}
        self._lock = RLock()

    def create_session(self, data: dict[str, Any]) -> str:
        """Create a session and return its opaque identifier."""
        session_id = token_urlsafe(32)
        with self._lock:
            self._sessions[session_id] = deepcopy(data)
        return session_id

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        """Return an active session, deleting it when expired."""
        with self._lock:
            session = self._sessions.get(session_id)
            if not session or session["expires_at"] <= utcnow():
                self._sessions.pop(session_id, None)
                return None
            return deepcopy(session)

    def update_session(self, session_id: str, data: dict[str, Any]) -> bool:
        """Replace an active session and report whether it existed."""
        with self._lock:
            if self.get_session(session_id) is None:
                return False
            self._sessions[session_id] = deepcopy(data)
            return True

    def delete_session(self, session_id: str) -> bool:
        """Delete a session and report whether it existed."""
        with self._lock:
            return self._sessions.pop(session_id, None) is not None

    def create_state(self) -> str:
        """Create a one-time OAuth state with a short expiry."""
        state = token_urlsafe(32)
        with self._lock:
            self._states[state] = utcnow() + timedelta(minutes=self.state_minutes)
        return state

    def consume_state(self, state: str) -> bool:
        """Validate and consume an OAuth state exactly once."""
        with self._lock:
            expires_at = self._states.pop(state, None)
            return expires_at is not None and expires_at > utcnow()

    def cleanup_expired(self) -> None:
        """Remove expired sessions and OAuth states."""
        now = utcnow()
        with self._lock:
            self._sessions = {
                key: value
                for key, value in self._sessions.items()
                if value["expires_at"] > now
            }
            self._states = {
                key: value for key, value in self._states.items() if value > now
            }

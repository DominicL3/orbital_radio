"""
Pytest configuration and shared fixtures for Orbital Radio backend tests.

This module provides common fixtures and test configuration for all test modules
in the Orbital Radio backend test suite.
"""

import os
import sqlite3
import tempfile
from collections.abc import Generator
from datetime import timedelta
from pathlib import Path
from typing import Any

import pytest

from src.config import utcnow

os.environ.setdefault("SPOTIFY_CLIENT_ID", "test-client-id-not-a-credential")
os.environ.setdefault("SPOTIFY_CLIENT_SECRET", "test-client-secret-not-a-credential")
os.environ.setdefault("SPOTIFY_REDIRECT_URI", "http://localhost:8000/test-callback")


# Mock database connection for testing
@pytest.fixture
def in_memory_db() -> Generator[str, None, None]:
    """
    Create an in-memory SQLite database for testing.

    Returns:
        str: Database connection string for in-memory SQLite database.
    """
    db_path = ":memory:"
    yield db_path


@pytest.fixture
def temp_db_file() -> Generator[str, None, None]:
    """
    Create a temporary SQLite database file for testing.

    Returns:
        str: Path to temporary database file.
    """
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
        db_path = tmp_file.name

    yield db_path

    # Cleanup
    Path(db_path).unlink(missing_ok=True)


@pytest.fixture
def mock_spotify_tokens() -> dict[str, Any]:
    """
    Create mock Spotify tokens for testing.

    Returns:
        Dict[str, Any]: Mock Spotify token data.
    """
    return {
        "access_token": "mock_access_token_12345",
        "refresh_token": "mock_refresh_token_67890",
        "expires_at": utcnow() + timedelta(hours=1),
        "token_type": "Bearer",
        "scope": "user-read-private user-read-email streaming",
    }


@pytest.fixture
def mock_user_profile() -> dict[str, Any]:
    """
    Create mock user profile data for testing.

    Returns:
        Dict[str, Any]: Mock user profile data.
    """
    return {
        "display_name": "Test User",
        "spotify_user_id": "test_user_123",
        "email": "test@example.com",
        "country": "US",
        "product": "premium",
    }


@pytest.fixture
def mock_track_data() -> dict[str, Any]:
    """
    Create mock track data for testing.

    Returns:
        Dict[str, Any]: Mock track data.
    """
    return {
        "id": "track_123",
        "name": "Test Song",
        "artists": [{"name": "Test Artist"}],
        "album": {"name": "Test Album"},
        "duration_ms": 180000,  # 3 minutes
        "external_urls": {"spotify": "https://open.spotify.com/track/123"},
        "preview_url": "https://preview.spotify.com/123",
    }


@pytest.fixture
def mock_satellite_data() -> dict[str, Any]:
    """
    Create mock satellite data for testing.

    Returns:
        Dict[str, Any]: Mock satellite data.
    """
    return {
        "id": 1,
        "name": "International Space Station",
        "norad_id": 25544,
        "category": "iss",
        "tle_line1": "1 25544U 98067A   21001.00000000  .00001234  00000-0  12345-4 0  9999",
        "tle_line2": "2 25544  51.6400 123.4567   0001234  12.3456  78.9012 15.12345678123456",
        "tle_epoch": utcnow(),
        "is_active": True,
        "last_updated": utcnow(),
    }


@pytest.fixture
def mock_session_data(
    mock_spotify_tokens: dict[str, Any], mock_user_profile: dict[str, Any]
) -> dict[str, Any]:
    """
    Create mock session data for testing.

    Args:
        mock_spotify_tokens: Mock Spotify tokens fixture.
        mock_user_profile: Mock user profile fixture.

    Returns:
        Dict[str, Any]: Mock session data.
    """
    return {
        "session_id": "test_session_123",
        "spotify_tokens": mock_spotify_tokens,
        "user_profile": mock_user_profile,
        "current_orbital_session": {
            "satellite_id": "iss",
            "start_time": utcnow(),
            "tle_data": {},
            "playlist": [],
            "played_tracks": set(),
            "region_playlist_index": {},
        },
        "created_at": utcnow(),
        "expires_at": utcnow() + timedelta(hours=3),
    }


@pytest.fixture
def mock_tle_data() -> dict[str, Any]:
    """
    Create mock TLE data for testing.

    Returns:
        Dict[str, Any]: Mock TLE data.
    """
    return {
        "satellite_id": "25544",
        "name": "ISS (ZARYA)",
        "tle_line1": "1 25544U 98067A   21001.00000000  .00001234  00000-0  12345-4 0  9999",
        "tle_line2": "2 25544  51.6400 123.4567   0001234  12.3456  78.9012 15.12345678123456",
        "epoch": utcnow(),
        "fetch_time": utcnow(),
    }


@pytest.fixture
def mock_geographic_position() -> tuple[float, float]:
    """
    Create mock geographic position for testing.

    Returns:
        tuple[float, float]: Latitude and longitude coordinates.
    """
    return (40.7128, -74.0060)  # New York City coordinates


@pytest.fixture
def mock_playlist_tracks(mock_track_data: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Create mock playlist tracks for testing.

    Args:
        mock_track_data: Mock track data fixture.

    Returns:
        list[Dict[str, Any]]: List of mock track data.
    """
    tracks = []
    for i in range(10):
        track = mock_track_data.copy()
        track["id"] = f"track_{i}"
        track["name"] = f"Test Song {i}"
        track["duration_ms"] = 120000 + (i * 30000)  # 2-7 minutes
        tracks.append(track)
    return tracks


@pytest.fixture
def mock_cache_data() -> dict[str, Any]:
    """
    Create mock cache data for testing.

    Returns:
        Dict[str, Any]: Mock cache data.
    """
    return {
        "key1": "value1",
        "key2": {"nested": "data"},
        "key3": [1, 2, 3, 4, 5],
        "timestamps": {
            "key1": utcnow(),
            "key2": utcnow() - timedelta(minutes=30),
            "key3": utcnow() - timedelta(hours=1),
        },
    }


@pytest.fixture
def mock_db_connection(in_memory_db: str) -> sqlite3.Connection:
    """
    Create a mock database connection for testing.

    Args:
        in_memory_db: In-memory database fixture.

    Returns:
        sqlite3.Connection: Database connection object.
    """
    conn = sqlite3.connect(in_memory_db)
    conn.row_factory = sqlite3.Row

    # Create test tables
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            data TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS played_tracks (
            session_id TEXT,
            track_id TEXT,
            played_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (session_id, track_id)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS playback_positions (
            session_id TEXT,
            track_id TEXT,
            position_ms INTEGER,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (session_id, track_id)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS satellites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            norad_id INTEGER UNIQUE NOT NULL,
            category TEXT NOT NULL,
            tle_line1 TEXT NOT NULL,
            tle_line2 TEXT NOT NULL,
            tle_epoch TIMESTAMP NOT NULL,
            is_active BOOLEAN DEFAULT TRUE,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    return conn

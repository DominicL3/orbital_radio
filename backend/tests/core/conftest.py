"""
Shared test fixtures and configuration for core module tests.
"""

from datetime import datetime, timedelta
from typing import Any
from unittest.mock import Mock

import pytest


@pytest.fixture
def mock_tle_data() -> dict[str, Any]:
    """Mock TLE data for testing satellite tracking functionality."""
    return {
        "satellite_name": "ISS (ZARYA)",
        "line1": "1 25544U 98067A   23001.00000000  .00002182  00000-0  40768-4 0  9990",
        "line2": "2 25544  51.6461 339.7939 0001222  92.8340 267.3124 15.49309239366831",
        "epoch": datetime(2023, 1, 1, 0, 0, 0),
        "norad_id": 25544,
        "inclination": 51.6461,
        "raan": 339.7939,
        "eccentricity": 0.0001222,
        "arg_perigee": 92.8340,
        "mean_anomaly": 267.3124,
        "mean_motion": 15.49309239,
    }


@pytest.fixture
def mock_orbital_elements() -> dict[str, Any]:
    """Mock orbital elements for testing."""
    return {
        "inclination": 51.6461,
        "raan": 339.7939,
        "eccentricity": 0.0001222,
        "arg_perigee": 92.8340,
        "mean_anomaly": 267.3124,
        "mean_motion": 15.49309239,
        "epoch": datetime(2023, 1, 1, 0, 0, 0),
    }


@pytest.fixture
def mock_position_data() -> list[dict[str, Any]]:
    """Mock position data for satellite tracking tests."""
    return [
        {
            "timestamp": datetime(2023, 1, 1, 0, 0, 0),
            "latitude": 40.7128,
            "longitude": -74.0060,
            "altitude": 408.0,
        },
        {
            "timestamp": datetime(2023, 1, 1, 0, 5, 0),
            "latitude": 42.3601,
            "longitude": -71.0589,
            "altitude": 410.0,
        },
        {
            "timestamp": datetime(2023, 1, 1, 0, 10, 0),
            "latitude": 44.0522,
            "longitude": -68.2733,
            "altitude": 412.0,
        },
    ]


@pytest.fixture
def mock_geographic_region() -> dict[str, Any]:
    """Mock geographic region data for testing."""
    return {
        "country_code": "US",
        "country_name": "United States",
        "region": "North America",
        "continent": "North America",
        "is_ocean": False,
        "closest_country": None,
    }


@pytest.fixture
def mock_spotify_tracks() -> list[dict[str, Any]]:
    """Mock Spotify track data for playlist testing."""
    return [
        {
            "id": "track_1",
            "name": "Test Song 1",
            "artists": [{"name": "Test Artist 1"}],
            "duration_ms": 180000,  # 3 minutes
            "popularity": 85,
            "external_urls": {"spotify": "https://open.spotify.com/track/track_1"},
            "preview_url": "https://p.scdn.co/mp3-preview/track_1",
        },
        {
            "id": "track_2",
            "name": "Test Song 2",
            "artists": [{"name": "Test Artist 2"}],
            "duration_ms": 240000,  # 4 minutes
            "popularity": 78,
            "external_urls": {"spotify": "https://open.spotify.com/track/track_2"},
            "preview_url": "https://p.scdn.co/mp3-preview/track_2",
        },
        {
            "id": "track_3",
            "name": "Test Song 3",
            "artists": [{"name": "Test Artist 3"}],
            "duration_ms": 30000,  # 30 seconds (should be filtered out)
            "popularity": 92,
            "external_urls": {"spotify": "https://open.spotify.com/track/track_3"},
            "preview_url": "https://p.scdn.co/mp3-preview/track_3",
        },
        {
            "id": "track_4",
            "name": "Test Song 4",
            "artists": [{"name": "Test Artist 4"}],
            "duration_ms": 600000,  # 10 minutes (should be filtered out)
            "popularity": 65,
            "external_urls": {"spotify": "https://open.spotify.com/track/track_4"},
            "preview_url": "https://p.scdn.co/mp3-preview/track_4",
        },
    ]


@pytest.fixture
def mock_user_tokens() -> dict[str, Any]:
    """Mock Spotify user tokens for authentication tests."""
    return {
        "access_token": "BQC4liRpFVf9b37PRdqMAZBylPxkjIhNAXQBSBhN3wWgAJhWHEKMvfCe8pQhCt8dLjgLDCvHQaEqYKmOF7cJrfGKQ-rIEDr-1nP0_oIoXXOZmLnXOdTgGUlJvpj5lfX3mZmK7rJ7qgNKKuMNzxA",
        "token_type": "Bearer",
        "expires_in": 3600,
        "refresh_token": "AQCn5Q3MNJHkV_zUz_v7qmZ9e4r8vPhJa_nOzPYdNWYOlNqQn1gVMvjGfuKHQzOQKUzQKxpZFvY2tGhJ5kP8bZPYhAQIJJHK5lXWCdFjNBvQHVxXzAcaVKpJGdBdY7wPNzLxOqXgKsVFDGnBH6hEjKfVmSZaOqYGlNXFnZZVYVAjKN",
        "scope": "user-read-private user-read-email streaming user-read-playback-state user-modify-playback-state",
    }


@pytest.fixture
def mock_user_profile() -> dict[str, Any]:
    """Mock Spotify user profile for testing."""
    return {
        "id": "test_user_123",
        "display_name": "Test User",
        "email": "test@example.com",
        "country": "US",
        "followers": {"total": 100},
        "images": [{"url": "https://example.com/avatar.jpg"}],
        "product": "premium",
    }


@pytest.fixture
def mock_session_data() -> dict[str, Any]:
    """Mock session data for testing."""
    return {
        "session_id": "test_session_123",
        "spotify_tokens": {
            "access_token": "test_access_token",
            "refresh_token": "test_refresh_token",
            "expires_at": datetime.now() + timedelta(hours=1),
        },
        "user_profile": {
            "display_name": "Test User",
            "spotify_user_id": "test_user_123",
        },
        "current_orbital_session": {
            "satellite_id": "iss",
            "start_time": datetime.now(),
            "tle_data": {},
            "playlist": [],
            "played_tracks": set(),
            "region_playlist_index": {},
        },
        "created_at": datetime.now(),
        "expires_at": datetime.now() + timedelta(hours=3),
    }


@pytest.fixture
def mock_celestrak_response() -> str:
    """Mock CelesTrak API response for TLE data."""
    return """ISS (ZARYA)
1 25544U 98067A   23001.00000000  .00002182  00000-0  40768-4 0  9990
2 25544  51.6461 339.7939 0001222  92.8340 267.3124 15.49309239366831
NOAA 18
1 28654U 05018A   23001.00000000  .00000146  00000-0  79304-4 0  9994
2 28654  99.0533 155.9789 0014108 152.0651 208.1844 14.12497342905123"""


@pytest.fixture
def mock_spotify_search_response() -> dict[str, Any]:
    """Mock Spotify search API response."""
    return {
        "tracks": {
            "items": [
                {
                    "id": "track_1",
                    "name": "Test Song 1",
                    "artists": [{"name": "Test Artist 1", "id": "artist_1"}],
                    "duration_ms": 180000,
                    "popularity": 85,
                    "external_urls": {
                        "spotify": "https://open.spotify.com/track/track_1"
                    },
                    "preview_url": "https://p.scdn.co/mp3-preview/track_1",
                    "album": {"name": "Test Album 1", "id": "album_1"},
                }
            ],
            "total": 1,
            "limit": 50,
            "offset": 0,
        }
    }


@pytest.fixture
def mock_spotify_playlist_response() -> dict[str, Any]:
    """Mock Spotify playlist API response."""
    return {
        "playlists": {
            "items": [
                {
                    "id": "playlist_1",
                    "name": "Top 50 - United States",
                    "description": "Your daily update of the most played tracks in United States",
                    "tracks": {
                        "items": [
                            {
                                "track": {
                                    "id": "track_1",
                                    "name": "Test Song 1",
                                    "artists": [{"name": "Test Artist 1"}],
                                    "duration_ms": 180000,
                                    "popularity": 85,
                                }
                            }
                        ]
                    },
                }
            ]
        }
    }


@pytest.fixture
def mock_requests_get():
    """Mock requests.get for HTTP calls."""
    mock = Mock()
    mock.return_value.status_code = 200
    mock.return_value.json.return_value = {}
    mock.return_value.text = ""
    return mock


@pytest.fixture
def mock_requests_post():
    """Mock requests.post for HTTP calls."""
    mock = Mock()
    mock.return_value.status_code = 200
    mock.return_value.json.return_value = {}
    return mock


@pytest.fixture
def mock_datetime_now():
    """Mock datetime.now() for consistent testing."""
    return datetime(2023, 1, 1, 12, 0, 0)


@pytest.fixture
def played_tracks_set() -> set:
    """Mock set of played track IDs."""
    return {"track_1", "track_3", "track_5"}


@pytest.fixture
def mock_country_codes() -> list[str]:
    """Mock list of country codes for testing."""
    return ["US", "CA", "GB", "FR", "DE", "JP", "AU", "BR", "IN", "MX"]


@pytest.fixture
def mock_ocean_coordinates() -> tuple:
    """Mock coordinates for ocean testing."""
    return (30.0, -60.0)  # Atlantic Ocean


@pytest.fixture
def mock_land_coordinates() -> tuple:
    """Mock coordinates for land testing."""
    return (40.7128, -74.0060)  # New York City


@pytest.fixture
def mock_satellite_data() -> dict[str, Any]:
    """Mock satellite data for database tests."""
    return {
        "id": 1,
        "name": "International Space Station",
        "norad_id": 25544,
        "category": "iss",
        "tle_line1": "1 25544U 98067A   23001.00000000  .00002182  00000-0  40768-4 0  9990",
        "tle_line2": "2 25544  51.6461 339.7939 0001222  92.8340 267.3124 15.49309239366831",
        "tle_epoch": datetime(2023, 1, 1, 0, 0, 0),
        "is_active": True,
        "last_updated": datetime(2023, 1, 1, 0, 0, 0),
    }

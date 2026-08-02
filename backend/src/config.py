"""Configuration settings for Orbital Radio backend.

Centralizes environment variables, application settings, and satellite catalog.
"""

from datetime import datetime, timezone
from functools import lru_cache
from typing import Any, Dict


VALID_SATELLITE_CATEGORIES: set[str] = {
    "iss",
    "weather",
    "starlink",
    "remote_sensing",
    "navigation",
    "earth_observation",
    "communication",
}

def utcnow() -> datetime:
    """Return a naive datetime representing the current UTC time.

    Replaces the deprecated ``datetime.utcnow()`` with a compatible equivalent.
    Returns:
        datetime: Current UTC time with no timezone info attached.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


# Hard-coded ISS TLE fixture used as fallback when real TLE data is unavailable.
ISS_FALLBACK_TLE_LINE1 = "1 25544U 98067A   21001.00000000  .00001234  00000-0  12345-4 0  9990"
ISS_FALLBACK_TLE_LINE2 = "2 25544  51.6464 123.4567  0003456 123.4567 234.5678 15.49123456123456"


class Settings:
    """Application settings loaded from environment or defaults."""

    # Application
    environment: str = "development"
    log_level: str = "INFO"
    secret_key: str = "dev-secret-change-in-production"

    # Database
    database_path: str = "./orbital_radio.db"

    # Spotify API
    spotify_client_id: str = ""
    spotify_client_secret: str = ""
    spotify_redirect_uri: str = "http://localhost:8000/auth/spotify/callback"

    # Session Management
    session_expire_hours: int = 3
    max_played_tracks_per_session: int = 500

    # Playlist Generation
    country_cooldown_songs: int = 5
    playlist_cache_max_age_hours: int = 24
    prefetch_playlists_on_startup: bool = True

    # Geographic Data
    country_boundaries_file: str = "./data/country_boundaries.geojson"

    # Satellite Catalog (MVP: ISS, extensible)
    satellite_catalog: Dict[str, Dict[str, Any]] = {
        "iss": {
            "name": "International Space Station",
            "norad_id": 25544,
            "category": "iss",
            "celestrak_url": "https://celestrak.org/NORAD/elements/stations.txt",
        }
    }


@lru_cache()
def get_settings() -> Settings:
    """Get cached global settings instance.

    Returns:
        Settings: Application configuration settings.
    """
    return Settings()

"""Configuration settings for Orbital Radio backend.

Centralizes environment variables, application settings, and satellite catalog.
"""

from datetime import UTC, datetime
from os import environ
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

# Local development uses an .env file in the repo root, but in prod, environment
# variables are sourced from Railway Variables or whatever deployment platform
PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env", override=False)


def utcnow() -> datetime:
    """Return a naive datetime representing the current UTC time.

    Replaces the deprecated ``datetime.utcnow()`` with a compatible equivalent.
    Returns:
        datetime: Current UTC time with no timezone info attached.
    """
    return datetime.now(UTC).replace(tzinfo=None)


class Settings:
    """All application configuration loaded from environment or safe defaults."""

    # Application
    def __init__(self) -> None:
        """Load application settings from environment variables."""
        self.environment = environ.get("ENVIRONMENT", "development").strip().lower()
        self.log_level = environ.get("LOG_LEVEL", "INFO").strip().upper()
        self.secret_key = environ.get("SECRET_KEY", "dev-secret-change-in-production")
        if self.environment == "production" and (
            self.secret_key == "dev-secret-change-in-production"
            or len(self.secret_key) < 32
        ):
            raise ValueError("A strong SECRET_KEY is required in production")

        # Database
        self.database_path = environ.get("DATABASE_PATH", "./orbital_radio.db")

        # Spotify API
        self.spotify_client_id = environ.get("SPOTIFY_CLIENT_ID", "").strip()
        self.spotify_client_secret = environ.get("SPOTIFY_CLIENT_SECRET", "").strip()
        self.spotify_redirect_uri = environ.get(
            "SPOTIFY_REDIRECT_URI",
            "http://localhost:8000/auth/spotify/callback",
        ).strip()

        # Session Management
        self.session_expire_hours = int(environ.get("SESSION_EXPIRE_HOURS", "3"))
        self.oauth_state_minutes = int(environ.get("OAUTH_STATE_MINUTES", "10"))
        self.max_played_tracks_per_session = int(
            environ.get("MAX_PLAYED_TRACKS_PER_SESSION", "500")
        )

        # Satellite Data & Refresh Timing
        self.tle_refresh_hours = int(environ.get("TLE_REFRESH_HOURS", "12"))
        self.tle_stale_hours = int(environ.get("TLE_STALE_HOURS", "12"))

        # Playlist Generation
        self.country_cooldown_songs = int(environ.get("COUNTRY_COOLDOWN_SONGS", "5"))
        self.playlist_cache_max_age_hours = int(
            environ.get("PLAYLIST_CACHE_MAX_AGE_HOURS", "24")
        )
        self.prefetch_playlists_on_startup = environ.get(
            "PREFETCH_PLAYLISTS_ON_STARTUP", "true"
        ).lower() in {"1", "true", "yes"}

        # Geographic Data
        self.country_boundaries_file = environ.get(
            "COUNTRY_BOUNDARIES_FILE", "./data/country_boundaries.geojson"
        )

        # Satellite data
        self.valid_satellite_categories: set[str] = {
            "iss",
            "weather",
            "starlink",
            "remote_sensing",
            "navigation",
            "earth_observation",
            "communication",
        }
        self.iss_fallback_tle_line1 = (
            "1 25544U 98067A   21001.00000000  .00001234  00000-0  12345-4 0  9990"
        )
        self.iss_fallback_tle_line2 = (
            "2 25544  51.6464 123.4567  0003456 123.4567 234.5678 15.49123456123456"
        )
        self.satellite_catalog: dict[str, dict[str, Any]] = {
            "iss": {
                "name": "International Space Station",
                "norad_id": 25544,
                "category": "iss",
                "celestrak_url": "https://celestrak.org/NORAD/elements/stations.txt",
            }
        }

    @property
    def cors_origins(self) -> list[str]:
        """Return configured, explicit browser origins."""
        value = environ.get(
            "CORS_ORIGINS", "http://localhost:3000,http://localhost:8000"
        )
        return [origin.strip() for origin in value.split(",") if origin.strip()]


def get_settings() -> Settings:
    """Get the current global settings instance.

    Returns:
        Settings: Application configuration settings.
    """
    return Settings()

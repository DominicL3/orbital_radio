"""Configuration settings for the Orbital Radio backend.

The application is anonymous and has no provider credentials, cookies, or
server-side user sessions.  Settings here cover the satellite maintenance
job, offline geographic data, and on-demand Radio Browser metadata requests.
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

        # Database
        self.database_path = environ.get("DATABASE_PATH", "./orbital_radio.db")

        # Satellite Data & Refresh Timing
        self.tle_refresh_hours = int(environ.get("TLE_REFRESH_HOURS", "12"))
        self.tle_stale_hours = int(environ.get("TLE_STALE_HOURS", "12"))

        # Geographic Data
        self.country_boundaries_file = environ.get(
            "COUNTRY_BOUNDARIES_FILE", "./data/country_boundaries.geojson"
        )

        # Radio Browser metadata requests.  These values intentionally do not
        # include station audio settings: audio goes directly from a selected
        # broadcaster to the browser and is never fetched by this service.
        self.radio_browser_user_agent = environ.get(
            "RADIO_BROWSER_USER_AGENT", "OrbitalRadio/0.1"
        ).strip()
        self.radio_request_timeout_seconds = float(
            environ.get("RADIO_REQUEST_TIMEOUT_SECONDS", "5")
        )
        self.radio_result_limit = int(environ.get("RADIO_RESULT_LIMIT", "50"))
        self.radio_cache_ttl_minutes = int(environ.get("RADIO_CACHE_TTL_MINUTES", "30"))
        self.radio_failure_cache_minutes = int(
            environ.get("RADIO_FAILURE_CACHE_MINUTES", "10")
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
            "CORS_ORIGINS",
            "http://localhost:4174,http://127.0.0.1:4174",
        )
        return [origin.strip() for origin in value.split(",") if origin.strip()]


def get_settings() -> Settings:
    """Get the current global settings instance.

    Returns:
        Settings: Application configuration settings.
    """
    return Settings()

"""Tests for the anonymous backend configuration."""

from os import environ
from unittest.mock import patch

from src.config import Settings, get_settings


def test_settings_defaults() -> None:
    """Use documented safe defaults without provider credentials."""
    with patch.dict(environ, {}, clear=True):
        settings = Settings()
        assert settings.environment == "development"
        assert settings.log_level == "INFO"
        assert settings.database_path == "./orbital_radio.db"
        assert settings.tle_refresh_hours == 12
        assert settings.tle_stale_hours == 12
        assert settings.country_boundaries_file == "./data/country_boundaries.geojson"
        assert settings.radio_browser_user_agent == "OrbitalRadio/0.1"
        assert settings.radio_request_timeout_seconds == 5
        assert settings.radio_result_limit == 50
        assert settings.radio_cache_ttl_minutes == 30
        assert settings.radio_failure_cache_minutes == 10
        assert settings.cors_origins == [
            "http://localhost:4174",
            "http://127.0.0.1:4174",
        ]
        assert not hasattr(settings, "secret_key")


def test_radio_settings_parse_environment() -> None:
    """Parse radio metadata settings from environment variables."""
    with patch.dict(
        environ,
        {
            "RADIO_BROWSER_USER_AGENT": " Orbital Radio/test ",
            "RADIO_REQUEST_TIMEOUT_SECONDS": "2.5",
            "RADIO_RESULT_LIMIT": "25",
            "RADIO_CACHE_TTL_MINUTES": "45",
            "RADIO_FAILURE_CACHE_MINUTES": "7",
        },
        clear=True,
    ):
        settings = Settings()
        assert settings.radio_browser_user_agent == "Orbital Radio/test"
        assert settings.radio_request_timeout_seconds == 2.5
        assert settings.radio_result_limit == 25
        assert settings.radio_cache_ttl_minutes == 45
        assert settings.radio_failure_cache_minutes == 7


def test_cors_origins_parsing() -> None:
    """Parse comma-separated, trimmed origins."""
    with patch.dict(
        environ,
        {"CORS_ORIGINS": " https://example.com , http://127.0.0.1:4174 "},
        clear=True,
    ):
        settings = Settings()
        assert settings.cors_origins == [
            "https://example.com",
            "http://127.0.0.1:4174",
        ]


def test_get_settings_factory() -> None:
    """Return a Settings instance from the factory."""
    assert isinstance(get_settings(), Settings)

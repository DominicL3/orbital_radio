"""Unit tests for centralized application settings in src.config."""

from unittest.mock import patch

import pytest

from src.config import Settings, get_settings


def test_settings_defaults() -> None:
    """Verify default values when environment is empty."""
    with patch.dict("os.environ", {}, clear=True):
        settings = Settings()
        assert settings.environment == "development"
        assert settings.log_level == "INFO"
        assert settings.database_path == "./orbital_radio.db"
        assert settings.session_expire_hours == 3
        assert settings.oauth_state_minutes == 10
        assert settings.tle_refresh_hours == 12
        assert settings.tle_stale_hours == 12
        assert "iss" in settings.valid_satellite_categories
        assert settings.iss_fallback_tle_line1.startswith("1 25544")
        assert settings.iss_fallback_tle_line2.startswith("2 25544")
        assert settings.cors_origins == [
            "http://localhost:3000",
            "http://localhost:8000",
        ]


def test_settings_production_requires_strong_secret() -> None:
    """Production environment requires a non-default secret key of at least 32 chars."""
    with patch.dict(
        "os.environ",
        {"ENVIRONMENT": "production", "SECRET_KEY": "dev-secret-change-in-production"},
        clear=True,
    ):
        with pytest.raises(ValueError, match="strong SECRET_KEY"):
            Settings()

    with patch.dict(
        "os.environ",
        {"ENVIRONMENT": "production", "SECRET_KEY": "too-short"},
        clear=True,
    ):
        with pytest.raises(ValueError, match="strong SECRET_KEY"):
            Settings()

    with patch.dict(
        "os.environ",
        {
            "ENVIRONMENT": "production",
            "SECRET_KEY": "a-sufficiently-long-production-secret-key-12345",
        },
        clear=True,
    ):
        settings = Settings()
        assert (
            settings.secret_key == "a-sufficiently-long-production-secret-key-12345"
        )


def test_cors_origins_parsing() -> None:
    """CORS_ORIGINS parses comma-separated trimmed origins."""
    with patch.dict(
        "os.environ",
        {"CORS_ORIGINS": " https://example.com , http://localhost:3000 "},
        clear=True,
    ):
        settings = Settings()
        assert settings.cors_origins == [
            "https://example.com",
            "http://localhost:3000",
        ]


def test_get_settings_factory() -> None:
    """get_settings returns a configured Settings instance."""
    settings = get_settings()
    assert isinstance(settings, Settings)

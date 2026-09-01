"""Shared fixtures for the anonymous Orbital Radio backend tests."""

import sqlite3
import tempfile
from collections.abc import Generator
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest

from src.config import utcnow


@pytest.fixture
def in_memory_db() -> Generator[str, None, None]:
    """Provide an in-memory SQLite connection path for repository tests."""
    yield ":memory:"


@pytest.fixture
def temp_db_file() -> Generator[str, None, None]:
    """Provide a temporary SQLite database file and remove it afterwards."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
        db_path = tmp_file.name
    try:
        yield db_path
    finally:
        Path(db_path).unlink(missing_ok=True)


@pytest.fixture
def mock_satellite_data() -> dict[str, Any]:
    """Representative ISS database response data."""
    now = utcnow()
    return {
        "id": 1,
        "name": "International Space Station",
        "norad_id": 25544,
        "category": "iss",
        "tle_line1": "1 25544U 98067A   21001.00000000  .00001234  00000-0  12345-4 0  9999",
        "tle_line2": "2 25544  51.6400 123.4567   0001234  12.3456  78.9012 15.12345678123456",
        "tle_epoch": now,
        "is_active": True,
        "last_updated": now,
    }


@pytest.fixture
def mock_tle_data() -> dict[str, Any]:
    """Representative TLE data for satellite service tests."""
    now = utcnow()
    return {
        "satellite_id": "iss",
        "name": "International Space Station",
        "norad_id": 25544,
        "tle_line1": "1 25544U 98067A   21001.00000000  .00001234  00000-0  12345-4 0  9999",
        "tle_line2": "2 25544  51.6400 123.4567   0001234  12.3456  78.9012 15.12345678123456",
        "epoch": now,
        "is_active": True,
    }


@pytest.fixture
def mock_geographic_position() -> tuple[float, float]:
    """Representative land coordinates (New York City)."""
    return 40.7128, -74.0060


@pytest.fixture
def mock_land_coordinates() -> tuple[float, float]:
    """Representative land coordinates for API and mapper tests."""
    return 40.7128, -74.0060


@pytest.fixture
def mock_ocean_coordinates() -> tuple[float, float]:
    """Representative open-ocean coordinates."""
    return 30.0, -60.0


@pytest.fixture
def mock_cache_data() -> dict[str, Any]:
    """Generic cache payload for cache utility tests."""
    return {
        "key1": "value1",
        "key2": {"nested": "data"},
        "key3": [1, 2, 3, 4, 5],
        "timestamps": {
            "key1": utcnow(),
            "key2": datetime.fromtimestamp(0),
            "key3": datetime.fromtimestamp(0),
        },
    }


@pytest.fixture
def mock_db_connection(in_memory_db: str) -> sqlite3.Connection:
    """Provide a SQLite connection containing only satellite persistence tables."""
    connection = sqlite3.connect(in_memory_db)
    connection.row_factory = sqlite3.Row
    connection.execute(
        """
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
        """
    )
    connection.commit()
    return connection

"""Shared fixtures for backend core tests."""

from datetime import datetime
from typing import Any

import pytest


@pytest.fixture
def mock_tle_data() -> dict[str, Any]:
    """Mock TLE data for satellite tracking tests."""
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
    """Mock orbital elements for satellite tests."""
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
def mock_celestrak_response() -> str:
    """Mock CelesTrak response containing two satellites."""
    return """ISS (ZARYA)
1 25544U 98067A   23001.00000000  .00002182  00000-0  40768-4 0  9990
2 25544  51.6461 339.7939 0001222  92.8340 267.3124 15.49309239366831
NOAA 18
1 28654U 05018A   23001.00000000  .00000146  00000-0  79304-4 0  9994
2 28654  99.0533 155.9789 0014108 152.0651 208.1844 14.12497342905123"""

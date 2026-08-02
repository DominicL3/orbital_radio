"""
Comprehensive unit tests for satellite API endpoints.

Tests cover satellite listing, details retrieval, TLE data access, position calculations,
and error handling with proper mocking of external dependencies.
"""

import pytest
from unittest.mock import patch
from datetime import datetime, timedelta
from typing import Dict, List, Any
from fastapi.testclient import TestClient
from fastapi import status
import math

# Import test fixtures from conftest


class TestSatelliteEndpoints:
    """Test suite for satellite API endpoints."""

    @pytest.fixture
    def client(self) -> TestClient:
        """Create FastAPI test client."""
        from src.main import app
        return TestClient(app)

    @pytest.fixture
    def mock_satellite_list(
        self, mock_satellite_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Mock list of satellites."""
        satellites = []
        satellite_configs = [
            {
                "id": 1,
                "name": "International Space Station",
                "norad_id": 25544,
                "category": "iss",
            },
            {"id": 2, "name": "NOAA 18", "norad_id": 28654, "category": "weather"},
            {
                "id": 3,
                "name": "Terra",
                "norad_id": 25994,
                "category": "earth_observation",
            },
            {
                "id": 4,
                "name": "Aqua",
                "norad_id": 27424,
                "category": "earth_observation",
            },
            {
                "id": 5,
                "name": "Starlink-1007",
                "norad_id": 44713,
                "category": "starlink",
            },
        ]

        for config in satellite_configs:
            satellite = mock_satellite_data.copy()
            satellite.update(config)
            satellites.append(satellite)

        return satellites

    @pytest.fixture
    def mock_tle_response(self) -> Dict[str, Any]:
        """Mock TLE data response."""
        return {
            "satellite_id": "25544",
            "name": "ISS (ZARYA)",
            "norad_id": 25544,
            "tle_line1": "1 25544U 98067A   23001.00000000  .00002182  00000-0  40768-4 0  9990",
            "tle_line2": "2 25544  51.6461 339.7939 0001222  92.8340 267.3124 15.49309239366831",
            "epoch": datetime.utcnow().isoformat(),
            "last_updated": datetime.utcnow().isoformat(),
        }

    @pytest.fixture
    def mock_positions_response(self) -> List[Dict[str, Any]]:
        """Mock satellite position predictions."""
        positions = []
        start_time = datetime.utcnow()

        for i in range(10):
            positions.append(
                {
                    "timestamp": (start_time + timedelta(minutes=i * 5)).isoformat(),
                    "latitude": 40.0 + (i * 2.5),
                    "longitude": -74.0 + (i * 3.0),
                    "altitude": 408.0 + (i * 0.5),
                    "velocity": 7.66,
                }
            )

        return positions

    def test_get_satellites_list_success(
        self, client: TestClient, mock_satellite_list: List[Dict[str, Any]]
    ):
        """Test successful retrieval of satellites list."""
        with patch("src.services.satellite_service.SatelliteService") as mock_service:
            mock_service.return_value.get_all_satellites.return_value = (
                mock_satellite_list
            )

            # Act
            response = client.get("/satellites")

            # Assert
            assert response.status_code == status.HTTP_200_OK
            response_data = response.json()
            assert "satellites" in response_data
            assert len(response_data["satellites"]) == 5

            # Verify ISS is in the list
            iss_satellite = next(
                (
                    s
                    for s in response_data["satellites"]
                    if s["name"] == "International Space Station"
                ),
                None,
            )
            assert iss_satellite is not None
            assert iss_satellite["norad_id"] == 25544
            assert iss_satellite["category"] == "iss"

            # Verify service call
            mock_service.return_value.get_all_satellites.assert_called_once()

    def test_get_satellites_list_filter_by_category(
        self, client: TestClient, mock_satellite_list: List[Dict[str, Any]]
    ):
        """Test filtering satellites by category."""
        # Filter to only weather satellites
        weather_satellites = [
            s for s in mock_satellite_list if s["category"] == "weather"
        ]

        with patch("src.services.satellite_service.SatelliteService") as mock_service:
            mock_service.return_value.get_satellites_by_category.return_value = (
                weather_satellites
            )

            # Act
            response = client.get("/satellites?category=weather")

            # Assert
            assert response.status_code == status.HTTP_200_OK
            response_data = response.json()
            assert "satellites" in response_data
            assert len(response_data["satellites"]) == 1
            assert response_data["satellites"][0]["category"] == "weather"
            assert response_data["satellites"][0]["name"] == "NOAA 18"

            # Verify service call
            mock_service.return_value.get_satellites_by_category.assert_called_once_with(
                "weather"
            )

    def test_get_satellites_list_filter_active_only(
        self, client: TestClient, mock_satellite_list: List[Dict[str, Any]]
    ):
        """Test filtering satellites to active only."""
        # Mark some satellites as inactive
        inactive_satellites = mock_satellite_list.copy()
        inactive_satellites[2]["is_active"] = False
        inactive_satellites[4]["is_active"] = False

        active_satellites = [s for s in inactive_satellites if s["is_active"]]

        with patch("src.services.satellite_service.SatelliteService") as mock_service:
            mock_service.return_value.get_active_satellites.return_value = (
                active_satellites
            )

            # Act
            response = client.get("/satellites?active_only=true")

            # Assert
            assert response.status_code == status.HTTP_200_OK
            response_data = response.json()
            assert "satellites" in response_data
            assert len(response_data["satellites"]) == 3
            assert all(s["is_active"] for s in response_data["satellites"])

            # Verify service call
            mock_service.return_value.get_active_satellites.assert_called_once()

    def test_get_satellites_list_empty_result(self, client: TestClient):
        """Test handling of empty satellites list."""
        with patch("src.services.satellite_service.SatelliteService") as mock_service:
            mock_service.return_value.get_all_satellites.return_value = []

            # Act
            response = client.get("/satellites")

            # Assert
            assert response.status_code == status.HTTP_200_OK
            response_data = response.json()
            assert "satellites" in response_data
            assert len(response_data["satellites"]) == 0

    def test_get_satellite_details_success(
        self, client: TestClient, mock_satellite_data: Dict[str, Any]
    ):
        """Test successful retrieval of satellite details."""
        satellite_id = "1"
        expected_satellite = mock_satellite_data.copy()
        expected_satellite["id"] = 1

        with patch("src.services.satellite_service.SatelliteService") as mock_service:
            mock_service.return_value.get_satellite_by_id.return_value = (
                expected_satellite
            )

            # Act
            response = client.get(f"/satellites/{satellite_id}")

            # Assert
            assert response.status_code == status.HTTP_200_OK
            response_data = response.json()
            assert response_data["id"] == 1
            assert response_data["name"] == "International Space Station"
            assert response_data["norad_id"] == 25544
            assert response_data["category"] == "iss"
            assert "tle_line1" in response_data
            assert "tle_line2" in response_data
            assert "last_updated" in response_data

            # Verify service call
            mock_service.return_value.get_satellite_by_id.assert_called_once_with(
                int(satellite_id)
            )

    def test_get_satellite_details_not_found(self, client: TestClient):
        """Test satellite details retrieval for non-existent satellite."""
        with patch("src.services.satellite_service.SatelliteService") as mock_service:
            mock_service.return_value.get_satellite_by_id.return_value = None

            # Act
            response = client.get("/satellites/999")

            # Assert
            assert response.status_code == status.HTTP_404_NOT_FOUND
            response_data = response.json()
            assert "error" in response_data
            assert "not found" in response_data["error"].lower()

    def test_get_satellite_details_invalid_id(self, client: TestClient):
        """Test satellite details retrieval with invalid ID format."""
        invalid_ids = ["abc", "-1", "0", "999999", ""]

        for invalid_id in invalid_ids:
            response = client.get(f"/satellites/{invalid_id}")
            assert response.status_code in [
                status.HTTP_400_BAD_REQUEST,
                status.HTTP_404_NOT_FOUND,
                status.HTTP_422_UNPROCESSABLE_ENTITY,
            ]

    def test_get_satellite_tle_success(
        self, client: TestClient, mock_tle_response: Dict[str, Any]
    ):
        """Test successful retrieval of satellite TLE data."""
        satellite_id = "1"

        with patch("src.services.satellite_service.SatelliteService") as mock_service:
            mock_service.return_value.get_satellite_tle.return_value = mock_tle_response

            # Act
            response = client.get(f"/satellites/{satellite_id}/tle")

            # Assert
            assert response.status_code == status.HTTP_200_OK
            response_data = response.json()
            assert "tle_line1" in response_data
            assert "tle_line2" in response_data
            assert "epoch" in response_data
            assert "last_updated" in response_data
            assert response_data["norad_id"] == 25544
            assert "25544" in response_data["tle_line1"]
            assert "25544" in response_data["tle_line2"]

            # Verify service call
            mock_service.return_value.get_satellite_tle.assert_called_once_with(
                int(satellite_id)
            )

    def test_get_satellite_tle_not_found(self, client: TestClient):
        """Test TLE retrieval for non-existent satellite."""
        with patch("src.services.satellite_service.SatelliteService") as mock_service:
            mock_service.return_value.get_satellite_tle.return_value = None

            # Act
            response = client.get("/satellites/999/tle")

            # Assert
            assert response.status_code == status.HTTP_404_NOT_FOUND
            response_data = response.json()
            assert "error" in response_data
            assert "not found" in response_data["error"].lower()

    def test_get_satellite_tle_stale_data(
        self, client: TestClient, mock_tle_response: Dict[str, Any]
    ):
        """Test TLE retrieval when data is stale."""
        satellite_id = "1"

        # Mock stale TLE data (older than 24 hours)
        stale_tle = mock_tle_response.copy()
        stale_tle["last_updated"] = (
            datetime.utcnow() - timedelta(hours=25)
        ).isoformat()

        with patch("src.services.satellite_service.SatelliteService") as mock_service:
            mock_service.return_value.get_satellite_tle.return_value = stale_tle

            # Act
            response = client.get(f"/satellites/{satellite_id}/tle")

            # Assert
            assert response.status_code == status.HTTP_200_OK
            response_data = response.json()
            assert "warning" in response_data
            assert "stale" in response_data["warning"].lower()

    def test_get_satellite_positions_success(
        self, client: TestClient, mock_positions_response: List[Dict[str, Any]]
    ):
        """Test successful retrieval of satellite position predictions."""
        satellite_id = "1"
        duration_minutes = 90

        with patch("src.services.satellite_service.SatelliteService") as mock_service:
            mock_service.return_value.get_satellite_positions.return_value = (
                mock_positions_response
            )

            # Act
            response = client.get(
                f"/satellites/{satellite_id}/positions?duration_minutes={duration_minutes}"
            )

            # Assert
            assert response.status_code == status.HTTP_200_OK
            response_data = response.json()
            assert "positions" in response_data
            assert len(response_data["positions"]) == 10

            # Verify position data structure
            first_position = response_data["positions"][0]
            assert "timestamp" in first_position
            assert "latitude" in first_position
            assert "longitude" in first_position
            assert "altitude" in first_position
            assert "velocity" in first_position

            # Verify latitude/longitude ranges
            assert -90 <= first_position["latitude"] <= 90
            assert -180 <= first_position["longitude"] <= 180
            assert first_position["altitude"] > 0

            # Verify service call
            mock_service.return_value.get_satellite_positions.assert_called_once_with(
                int(satellite_id), duration_minutes
            )

    def test_get_satellite_positions_default_duration(
        self, client: TestClient, mock_positions_response: List[Dict[str, Any]]
    ):
        """Test satellite positions with default duration parameter."""
        satellite_id = "1"

        with patch("src.services.satellite_service.SatelliteService") as mock_service:
            mock_service.return_value.get_satellite_positions.return_value = (
                mock_positions_response
            )

            # Act - no duration parameter provided
            response = client.get(f"/satellites/{satellite_id}/positions")

            # Assert
            assert response.status_code == status.HTTP_200_OK
            response_data = response.json()
            assert "positions" in response_data

            # Verify service called with default duration (90 minutes)
            mock_service.return_value.get_satellite_positions.assert_called_once_with(
                int(satellite_id), 90
            )

    def test_get_satellite_positions_invalid_duration(self, client: TestClient):
        """Test satellite positions with invalid duration parameters."""
        satellite_id = "1"
        invalid_durations = [
            -30,
            0,
            1441,
            "abc",
            999999,
        ]  # Negative, zero, too large, non-numeric, excessive

        for duration in invalid_durations:
            response = client.get(
                f"/satellites/{satellite_id}/positions?duration_minutes={duration}"
            )
            assert response.status_code in [
                status.HTTP_400_BAD_REQUEST,
                status.HTTP_422_UNPROCESSABLE_ENTITY,
            ]

            if response.status_code == status.HTTP_400_BAD_REQUEST:
                response_data = response.json()
                assert "error" in response_data

    def test_get_satellite_positions_tle_unavailable(self, client: TestClient):
        """Test position calculation when TLE data is unavailable."""
        satellite_id = "1"

        with patch("src.services.satellite_service.SatelliteService") as mock_service:
            mock_service.return_value.get_satellite_positions.side_effect = ValueError(
                "TLE data not available"
            )

            # Act
            response = client.get(f"/satellites/{satellite_id}/positions")

            # Assert
            assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
            response_data = response.json()
            assert "error" in response_data
            assert "tle" in response_data["error"].lower()

    def test_get_satellite_positions_calculation_error(self, client: TestClient):
        """Test handling of orbital calculation errors."""
        satellite_id = "1"

        with patch("src.services.satellite_service.SatelliteService") as mock_service:
            mock_service.return_value.get_satellite_positions.side_effect = (
                RuntimeError("Orbital calculation failed")
            )

            # Act
            response = client.get(f"/satellites/{satellite_id}/positions")

            # Assert
            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            response_data = response.json()
            assert "error" in response_data
            assert "calculation" in response_data["error"].lower()

    @pytest.mark.parametrize(
        "satellite_category,expected_count",
        [
            ("iss", 1),
            ("weather", 1),
            ("earth_observation", 2),
            ("starlink", 1),
            ("communication", 0),  # No satellites in this category
        ],
    )
    def test_get_satellites_by_category_parametrized(
        self,
        client: TestClient,
        mock_satellite_list: List[Dict[str, Any]],
        satellite_category: str,
        expected_count: int,
    ):
        """Test satellite filtering by various categories."""
        filtered_satellites = [
            s for s in mock_satellite_list if s["category"] == satellite_category
        ]

        with patch("src.services.satellite_service.SatelliteService") as mock_service:
            mock_service.return_value.get_satellites_by_category.return_value = (
                filtered_satellites
            )

            # Act
            response = client.get(f"/satellites?category={satellite_category}")

            # Assert
            assert response.status_code == status.HTTP_200_OK
            response_data = response.json()
            assert len(response_data["satellites"]) == expected_count

            if expected_count > 0:
                assert all(
                    s["category"] == satellite_category
                    for s in response_data["satellites"]
                )

    def test_satellite_list_pagination(
        self, client: TestClient, mock_satellite_list: List[Dict[str, Any]]
    ):
        """Test pagination of satellite list."""
        page_size = 2
        page = 1

        # Mock paginated response
        paginated_satellites = mock_satellite_list[:page_size]

        with patch("src.services.satellite_service.SatelliteService") as mock_service:
            mock_service.return_value.get_satellites_paginated.return_value = {
                "satellites": paginated_satellites,
                "total_count": len(mock_satellite_list),
                "page": page,
                "page_size": page_size,
                "total_pages": 3,
            }

            # Act
            response = client.get(f"/satellites?page={page}&page_size={page_size}")

            # Assert
            assert response.status_code == status.HTTP_200_OK
            response_data = response.json()
            assert len(response_data["satellites"]) == page_size
            assert response_data["total_count"] == 5
            assert response_data["page"] == page
            assert response_data["page_size"] == page_size
            assert response_data["total_pages"] == 3

    def test_satellite_search_by_name(
        self, client: TestClient, mock_satellite_list: List[Dict[str, Any]]
    ):
        """Test searching satellites by name."""
        search_term = "space"
        matching_satellites = [
            s for s in mock_satellite_list if search_term.lower() in s["name"].lower()
        ]

        with patch("src.services.satellite_service.SatelliteService") as mock_service:
            mock_service.return_value.search_satellites_by_name.return_value = (
                matching_satellites
            )

            # Act
            response = client.get(f"/satellites?search={search_term}")

            # Assert
            assert response.status_code == status.HTTP_200_OK
            response_data = response.json()
            assert len(response_data["satellites"]) == 1
            assert "Space Station" in response_data["satellites"][0]["name"]

            # Verify service call
            mock_service.return_value.search_satellites_by_name.assert_called_once_with(
                search_term
            )

    def test_concurrent_satellite_requests(
        self, client: TestClient, mock_satellite_list: List[Dict[str, Any]]
    ):
        """Test handling of concurrent satellite data requests."""
        import threading

        results = []

        # Patch once before threads start (patch() is not thread-safe,
        # so applying it inside worker threads leaks the mock).
        with patch(
            "src.services.satellite_service.SatelliteService"
        ) as mock_service:
            mock_service.return_value.get_all_satellites.return_value = (
                mock_satellite_list
            )

            def make_request():
                try:
                    response = client.get("/satellites")
                    results.append(response.status_code == status.HTTP_200_OK)
                except Exception:
                    results.append(False)

            # Act - create multiple concurrent requests
            threads = []
            for _ in range(10):
                thread = threading.Thread(target=make_request)
                threads.append(thread)
                thread.start()

            for thread in threads:
                thread.join()

        # Assert - all requests should succeed
        assert len(results) == 10
        assert all(results)

    def test_satellite_data_freshness_check(
        self, client: TestClient, mock_satellite_list: List[Dict[str, Any]]
    ):
        """Test checking freshness of satellite data."""
        with patch("src.services.satellite_service.SatelliteService") as mock_service:
            # Mock service to return data with freshness info
            mock_service.return_value.get_all_satellites.return_value = (
                mock_satellite_list
            )
            mock_service.return_value.get_data_freshness.return_value = {
                "last_tle_update": datetime.utcnow().isoformat(),
                "next_scheduled_update": (
                    datetime.utcnow() + timedelta(hours=12)
                ).isoformat(),
                "stale_satellites": [],
            }

            # Act
            response = client.get("/satellites?include_freshness=true")

            # Assert
            assert response.status_code == status.HTTP_200_OK
            response_data = response.json()
            assert "data_freshness" in response_data
            assert "last_tle_update" in response_data["data_freshness"]
            assert "next_scheduled_update" in response_data["data_freshness"]

    def test_satellite_orbital_elements_extraction(
        self, client: TestClient, mock_tle_response: Dict[str, Any]
    ):
        """Test extraction of orbital elements from TLE data."""
        satellite_id = "1"

        # Enhanced TLE response with orbital elements
        enhanced_tle = mock_tle_response.copy()
        enhanced_tle["orbital_elements"] = {
            "inclination": 51.6461,
            "raan": 339.7939,
            "eccentricity": 0.0001222,
            "argument_of_perigee": 92.8340,
            "mean_anomaly": 267.3124,
            "mean_motion": 15.49309239,
            "epoch": datetime.utcnow().isoformat(),
        }

        with patch("src.services.satellite_service.SatelliteService") as mock_service:
            mock_service.return_value.get_satellite_tle.return_value = enhanced_tle

            # Act
            response = client.get(
                f"/satellites/{satellite_id}/tle?include_elements=true"
            )

            # Assert
            assert response.status_code == status.HTTP_200_OK
            response_data = response.json()
            assert "orbital_elements" in response_data
            elements = response_data["orbital_elements"]
            assert "inclination" in elements
            assert "raan" in elements
            assert "eccentricity" in elements
            assert elements["inclination"] == 51.6461

    def test_satellite_ground_track_calculation(self, client: TestClient):
        """Test calculation of satellite ground track."""
        satellite_id = "1"
        duration_minutes = 180  # 3 hours for multiple orbits

        # Mock ground track positions
        mock_ground_track = []
        start_time = datetime.utcnow()

        for i in range(36):  # 5-minute intervals for 3 hours
            lat = 51.6 * math.sin(i * 0.1)  # Simulate ISS-like orbit
            lon = (i * 15) % 360 - 180  # Westward progression
            mock_ground_track.append(
                {
                    "timestamp": (start_time + timedelta(minutes=i * 5)).isoformat(),
                    "latitude": lat,
                    "longitude": lon,
                    "altitude": 408.0,
                    "velocity": 7.66,
                }
            )

        with patch("src.services.satellite_service.SatelliteService") as mock_service:
            mock_service.return_value.get_satellite_positions.return_value = (
                mock_ground_track
            )

            # Act
            response = client.get(
                f"/satellites/{satellite_id}/positions?duration_minutes={duration_minutes}"
            )

            # Assert
            assert response.status_code == status.HTTP_200_OK
            response_data = response.json()
            assert "positions" in response_data
            assert len(response_data["positions"]) == 36

            # Verify orbital characteristics
            positions = response_data["positions"]
            latitudes = [p["latitude"] for p in positions]
            assert max(latitudes) <= 52  # ISS max latitude
            assert min(latitudes) >= -52  # ISS min latitude

    def test_satellite_visibility_windows(self, client: TestClient):
        """Test calculation of satellite visibility windows for a location."""
        satellite_id = "1"
        observer_lat = 40.7128  # New York City
        observer_lon = -74.0060

        mock_visibility = [
            {
                "start_time": datetime.utcnow().isoformat(),
                "end_time": (datetime.utcnow() + timedelta(minutes=6)).isoformat(),
                "max_elevation": 85.2,
                "max_elevation_time": (
                    datetime.utcnow() + timedelta(minutes=3)
                ).isoformat(),
                "brightness": -3.9,  # Very bright pass
            }
        ]

        with patch("src.services.satellite_service.SatelliteService") as mock_service:
            mock_service.return_value.get_visibility_windows.return_value = (
                mock_visibility
            )

            # Act
            response = client.get(
                f"/satellites/{satellite_id}/visibility?lat={observer_lat}&lon={observer_lon}"
            )

            # Assert
            assert response.status_code == status.HTTP_200_OK
            response_data = response.json()
            assert "visibility_windows" in response_data
            assert len(response_data["visibility_windows"]) == 1

            visibility_window = response_data["visibility_windows"][0]
            assert "start_time" in visibility_window
            assert "end_time" in visibility_window
            assert "max_elevation" in visibility_window
            assert visibility_window["max_elevation"] > 0

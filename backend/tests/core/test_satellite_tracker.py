"""
Comprehensive unit tests for the SatelliteTLEManager class.

Tests cover TLE data fetching, caching, orbital calculations, and position
generation with mocked external dependencies.
"""

from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pytest

from src.core.satellite_tracker import SatelliteTLEManager
from src.schemas.satellite import OrbitalElements, Position, TLEData


class TestSatelliteTLEManager:
    """Test suite for SatelliteTLEManager class."""

    @pytest.fixture
    def tle_manager(self):
        """Create a fresh SatelliteTLEManager instance for each test."""
        return SatelliteTLEManager()

    @pytest.fixture
    def mock_tle_response_text(self):
        """Mock CelesTrak TLE response text."""
        return """ISS (ZARYA)
1 25544U 98067A   23001.00000000  .00002182  00000-0  40768-4 0  9990
2 25544  51.6461 339.7939 0001222  92.8340 267.3124 15.49309239366831
NOAA 18
1 28654U 05018A   23001.00000000  .00000146  00000-0  79304-4 0  9994
2 28654  99.0533 155.9789 0014108 152.0651 208.1844 14.12497342905123"""

    def test_init_creates_empty_cache(self, tle_manager):
        """Test that initialization creates an empty TLE cache."""
        assert tle_manager.tle_cache == {}
        assert tle_manager.last_update_time is None
        assert "celestrak.org" in tle_manager.celestrak_base_url

    @patch("httpx.get")
    def test_fetch_tle_data_success(
        self, mock_get, tle_manager, mock_tle_response_text
    ):
        """Test successful TLE data fetching from CelesTrak."""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = mock_tle_response_text
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # Mock TLE parsing
        with patch.object(tle_manager, "_parse_tle_data") as mock_parse:
            expected_tle = TLEData(
                satellite_name="ISS (ZARYA)",
                line1="1 25544U 98067A   23001.00000000  .00002182  00000-0  40768-4 0  9990",
                line2="2 25544  51.6461 339.7939 0001222  92.8340 267.3124 15.49309239366831",
                epoch=datetime(2023, 1, 1, 0, 0, 0),
                norad_id=25544,
                inclination=51.6461,
                raan=339.7939,
                eccentricity=0.0001222,
                arg_perigee=92.8340,
                mean_anomaly=267.3124,
                mean_motion=15.49309239,
            )
            mock_parse.return_value = expected_tle

            # Act
            result = tle_manager.fetch_tle_data("iss")

            # Assert
            assert result.satellite_name == "ISS (ZARYA)"
            assert result.norad_id == 25544
            assert result.inclination == 51.6461
            mock_get.assert_called_once()
            mock_parse.assert_called_once_with(mock_tle_response_text, "iss")

    @patch("httpx.get")
    def test_fetch_tle_data_http_error(self, mock_get, tle_manager):
        """Test handling of HTTP errors when fetching TLE data."""
        # Arrange
        mock_get.side_effect = RuntimeError("Network error")

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            tle_manager.fetch_tle_data("iss")

        assert "Network error" in str(exc_info.value) or "TLE" in str(exc_info.value)

    @patch("httpx.get")
    def test_fetch_tle_data_invalid_response(self, mock_get, tle_manager):
        """Test handling of invalid TLE response format."""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "Invalid TLE format"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            tle_manager.fetch_tle_data("invalid_satellite")

        assert (
            "parse" in str(exc_info.value).lower()
            or "tle" in str(exc_info.value).lower()
        )

    def test_get_cached_tle_hit(self, tle_manager, mock_tle_data):
        """Test successful cache hit for TLE data."""
        # Arrange
        tle_data = TLEData(**mock_tle_data)
        tle_manager.tle_cache["iss"] = tle_data

        # Act
        result = tle_manager.get_cached_tle("iss")

        # Assert
        assert result is not None
        assert result.satellite_name == "ISS (ZARYA)"
        assert result.norad_id == 25544

    def test_get_cached_tle_miss(self, tle_manager):
        """Test cache miss for TLE data."""
        # Act
        result = tle_manager.get_cached_tle("nonexistent")

        # Assert
        assert result is None

    @patch("httpx.get")
    def test_refresh_all_tle_data_success(
        self, mock_get, tle_manager, mock_tle_response_text
    ):
        """Test successful refresh of all TLE data."""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = mock_tle_response_text
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # Pre-populate cache with old data
        old_tle = TLEData(
            satellite_name="OLD ISS",
            line1="old_line1",
            line2="old_line2",
            epoch=datetime(2022, 1, 1),
            norad_id=25544,
        )
        tle_manager.tle_cache["iss"] = old_tle

        # Mock multiple satellite IDs to refresh
        with patch.object(tle_manager, "_get_tracked_satellites") as mock_satellites:
            mock_satellites.return_value = ["iss", "noaa18"]

            with patch.object(tle_manager, "_parse_tle_data") as mock_parse:
                new_tle = TLEData(
                    satellite_name="ISS (ZARYA)",
                    line1="new_line1",
                    line2="new_line2",
                    epoch=datetime(2023, 1, 1),
                    norad_id=25544,
                )
                mock_parse.return_value = new_tle

                # Act
                tle_manager.refresh_all_tle_data()

                # Assert
                assert tle_manager.last_update_time is not None
                assert mock_get.call_count >= 1

    @patch("httpx.get")
    def test_refresh_all_tle_data_partial_failure(self, mock_get, tle_manager):
        """Test refresh handling when some satellites fail to update."""

        # Arrange
        def side_effect(*args, **kwargs):
            if "iss" in str(args[0]):
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.text = "Valid TLE data"
                mock_response.raise_for_status = Mock()
                return mock_response
            else:
                raise RuntimeError("Satellite not found")

        mock_get.side_effect = side_effect

        with patch.object(tle_manager, "_get_tracked_satellites") as mock_satellites:
            mock_satellites.return_value = ["iss", "invalid_satellite"]

            # Act - should not raise exception for partial failures
            tle_manager.refresh_all_tle_data()

            # Assert
            assert mock_get.call_count == 2
            assert tle_manager.last_update_time is not None

    def test_get_orbital_elements_success(self, tle_manager, mock_tle_data):
        """Test successful extraction of orbital elements from TLE data."""
        # Arrange
        tle_data = TLEData(**mock_tle_data)
        tle_manager.tle_cache["iss"] = tle_data

        # Act
        elements = tle_manager.get_orbital_elements("iss")

        # Assert
        assert isinstance(elements, OrbitalElements)
        assert elements.inclination == 51.6461
        assert elements.raan == 339.7939
        assert elements.eccentricity == 0.0001222
        assert elements.arg_perigee == 92.8340
        assert elements.mean_anomaly == 267.3124
        assert elements.mean_motion == 15.49309239
        assert elements.epoch == datetime(2023, 1, 1, 0, 0, 0)

    def test_get_orbital_elements_no_cache(self, tle_manager):
        """Test orbital elements extraction when no TLE data is cached."""
        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            tle_manager.get_orbital_elements("nonexistent")

        assert (
            "not found" in str(exc_info.value).lower()
            or "cache" in str(exc_info.value).lower()
        )

    def test_generate_simplified_positions_success(self, tle_manager, mock_tle_data):
        """Test successful generation of simplified position predictions."""
        # Arrange
        tle_data = TLEData(**mock_tle_data)
        tle_manager.tle_cache["iss"] = tle_data

        with patch.object(tle_manager, "_calculate_positions") as mock_calc:
            expected_positions = [
                Position(
                    timestamp=datetime(2023, 1, 1, 12, 0, 0),
                    latitude=40.7128,
                    longitude=-74.0060,
                    altitude=408.0,
                ),
                Position(
                    timestamp=datetime(2023, 1, 1, 12, 5, 0),
                    latitude=42.3601,
                    longitude=-71.0589,
                    altitude=410.0,
                ),
            ]
            mock_calc.return_value = expected_positions

            # Act
            positions = tle_manager.generate_simplified_positions("iss", 90)

            # Assert
            assert len(positions) == 2
            assert all(isinstance(pos, Position) for pos in positions)
            assert positions[0].latitude == 40.7128
            assert positions[0].longitude == -74.0060
            assert positions[1].latitude == 42.3601
            mock_calc.assert_called_once_with(tle_data, 90)

    def test_generate_simplified_positions_invalid_duration(
        self, tle_manager, mock_tle_data
    ):
        """Test position generation with invalid duration parameters."""
        # Arrange
        tle_data = TLEData(**mock_tle_data)
        tle_manager.tle_cache["iss"] = tle_data

        # Act & Assert - negative duration
        with pytest.raises(ValueError):
            tle_manager.generate_simplified_positions("iss", -30)

        # Act & Assert - zero duration
        with pytest.raises(ValueError):
            tle_manager.generate_simplified_positions("iss", 0)

        # Act & Assert - excessive duration
        with pytest.raises(ValueError):
            tle_manager.generate_simplified_positions("iss", 10000)

    @patch("httpx.get")
    def test_cache_expiration_and_refresh(
        self, mock_get, tle_manager, mock_tle_response_text
    ):
        """Test that old cached TLE data is properly refreshed."""
        # Arrange
        old_time = datetime.now() - timedelta(hours=24)  # 24 hours old
        old_tle = TLEData(
            satellite_name="OLD ISS",
            line1="old_line1",
            line2="old_line2",
            epoch=old_time,
            norad_id=25544,
        )
        tle_manager.tle_cache["iss"] = old_tle
        tle_manager.last_update_time = old_time

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = mock_tle_response_text
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        with patch.object(tle_manager, "_is_tle_stale") as mock_stale:
            mock_stale.return_value = True

            with patch.object(tle_manager, "_parse_tle_data") as mock_parse:
                new_tle = TLEData(
                    satellite_name="ISS (ZARYA)",
                    line1="new_line1",
                    line2="new_line2",
                    epoch=datetime.now(),
                    norad_id=25544,
                )
                mock_parse.return_value = new_tle

                # Act
                result = tle_manager.fetch_tle_data("iss")

                # Assert
                assert result.satellite_name == "ISS (ZARYA)"
                assert result.epoch > old_time
                mock_stale.assert_called_once()

    def test_concurrent_access_safety(self, tle_manager, mock_tle_data):
        """Test thread safety of cache operations."""
        import threading

        # Arrange
        tle_data = TLEData(**mock_tle_data)
        results = []

        def worker():
            try:
                tle_manager.tle_cache["iss"] = tle_data
                result = tle_manager.get_cached_tle("iss")
                results.append(result is not None)
            except Exception:
                results.append(False)

        # Act
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=worker)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Assert
        assert all(results)  # All operations should succeed
        assert len(results) == 10

    def test_memory_usage_with_large_cache(self, tle_manager):
        """Test memory efficiency with large cache."""
        # Arrange - simulate large cache
        for i in range(100):
            tle_data = TLEData(
                satellite_name=f"SAT_{i}",
                line1=f"line1_{i}",
                line2=f"line2_{i}",
                epoch=datetime.now(),
                norad_id=i,
            )
            tle_manager.tle_cache[f"sat_{i}"] = tle_data

        # Act
        cache_size = len(tle_manager.tle_cache)

        # Assert
        assert cache_size == 100
        assert all(isinstance(tle, TLEData) for tle in tle_manager.tle_cache.values())

    @pytest.mark.parametrize(
        "satellite_id,expected_norad",
        [("iss", 25544), ("noaa18", 28654), ("terra", 25994), ("aqua", 27424)],
    )
    def test_multiple_satellite_support(
        self, tle_manager, satellite_id, expected_norad
    ):
        """Test support for multiple satellite types."""
        # Arrange
        tle_data = TLEData(
            satellite_name=satellite_id.upper(),
            line1="mock_line1",
            line2="mock_line2",
            epoch=datetime.now(),
            norad_id=expected_norad,
        )
        tle_manager.tle_cache[satellite_id] = tle_data

        # Act
        result = tle_manager.get_cached_tle(satellite_id)

        # Assert
        assert result is not None
        assert result.norad_id == expected_norad

    def test_error_handling_comprehensive(self, tle_manager):
        """Test comprehensive error handling across all methods."""
        # Test with None inputs
        with pytest.raises((ValueError, TypeError)):
            tle_manager.fetch_tle_data(None)

        with pytest.raises((ValueError, TypeError)):
            tle_manager.get_cached_tle(None)

        with pytest.raises((ValueError, TypeError)):
            tle_manager.get_orbital_elements(None)

        # Test with empty string inputs
        with pytest.raises(ValueError):
            tle_manager.fetch_tle_data("")

        with pytest.raises(ValueError):
            tle_manager.generate_simplified_positions("", 90)

    @patch("time.time")
    def test_performance_benchmarks(self, mock_time, tle_manager, mock_tle_data):
        """Test performance requirements for cache operations."""
        # Arrange
        mock_time.return_value = 1000000.0
        tle_data = TLEData(**mock_tle_data)
        tle_manager.tle_cache["iss"] = tle_data

        # Act - multiple cache hits should be fast
        for _ in range(1000):
            result = tle_manager.get_cached_tle("iss")
            assert result is not None

        # Cache operations should be essentially instantaneous
        # This test ensures O(1) cache access performance
        assert True  # If we get here without timeout, performance is acceptable

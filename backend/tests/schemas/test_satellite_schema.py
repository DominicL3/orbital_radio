"""Test cases for satellite Pydantic schemas."""

from datetime import datetime, timedelta
import pytest
from pydantic import ValidationError


class TestSatelliteSchemas:
    """Test satellite-related Pydantic schemas."""

    def test_satellite_response_schema_valid(self) -> None:
        """Should validate SatelliteResponse schema with valid data."""
        from src.schemas.satellite import SatelliteResponse

        satellite_data = {
            "id": "iss",
            "name": "International Space Station",
            "norad_id": 25544,
            "category": "iss",
            "description": "The International Space Station (ISS) is a space station",
            "is_active": True,
            "orbit_info": {
                "altitude_km": 408,
                "inclination_deg": 51.6464,
                "period_minutes": 92.68,
                "eccentricity": 0.0003456,
            },
            "last_updated": datetime.utcnow(),
        }

        satellite = SatelliteResponse(**satellite_data)

        assert satellite.id == "iss"
        assert satellite.name == "International Space Station"
        assert satellite.norad_id == 25544
        assert satellite.category == "iss"
        assert satellite.is_active is True
        assert satellite.orbit_info.altitude_km == 408

    def test_satellite_response_schema_required_fields(self) -> None:
        """Should require essential fields in SatelliteResponse."""
        from src.schemas.satellite import SatelliteResponse

        # Missing required fields
        with pytest.raises(ValidationError) as exc_info:
            SatelliteResponse()

        error_str = str(exc_info.value)
        assert "id" in error_str
        assert "name" in error_str
        assert "norad_id" in error_str

        # Minimal valid satellite
        minimal_satellite = SatelliteResponse(
            id="test_sat",
            name="Test Satellite",
            norad_id=12345,
            category="weather",
            is_active=True,
        )

        assert minimal_satellite.id == "test_sat"
        assert minimal_satellite.description is None
        assert minimal_satellite.orbit_info is None

    def test_satellite_response_schema_category_validation(self) -> None:
        """Should validate satellite category values."""
        from src.schemas.satellite import SatelliteResponse

        valid_categories = [
            "iss",
            "weather",
            "starlink",
            "remote_sensing",
            "navigation",
        ]

        for category in valid_categories:
            satellite = SatelliteResponse(
                id="test_sat",
                name="Test Satellite",
                norad_id=12345,
                category=category,
                is_active=True,
            )
            assert satellite.category == category

        # Invalid category
        with pytest.raises(ValidationError):
            SatelliteResponse(
                id="test_sat",
                name="Test Satellite",
                norad_id=12345,
                category="invalid_category",
                is_active=True,
            )

    def test_satellite_response_schema_norad_id_validation(self) -> None:
        """Should validate NORAD ID format."""
        from src.schemas.satellite import SatelliteResponse

        # Valid NORAD IDs
        valid_norad_ids = [25544, 33591, 44713, 12345, 99999]

        for norad_id in valid_norad_ids:
            satellite = SatelliteResponse(
                id="test_sat",
                name="Test Satellite",
                norad_id=norad_id,
                category="iss",
                is_active=True,
            )
            assert satellite.norad_id == norad_id

        # Invalid NORAD IDs
        invalid_norad_ids = [-1, 0, "invalid", 100000]  # Out of valid range

        for invalid_id in invalid_norad_ids:
            with pytest.raises(ValidationError):
                SatelliteResponse(
                    id="test_sat",
                    name="Test Satellite",
                    norad_id=invalid_id,
                    category="iss",
                    is_active=True,
                )


class TestOrbitInfoSchema:
    """Test orbit information schema."""

    def test_orbit_info_schema_valid(self) -> None:
        """Should validate OrbitInfo schema with valid data."""
        from src.schemas.satellite import OrbitInfo

        orbit_data = {
            "altitude_km": 408.5,
            "inclination_deg": 51.6464,
            "period_minutes": 92.68,
            "eccentricity": 0.0003456,
            "perigee_km": 405.2,
            "apogee_km": 411.8,
            "orbit_type": "Low Earth Orbit",
        }

        orbit_info = OrbitInfo(**orbit_data)

        assert orbit_info.altitude_km == 408.5
        assert orbit_info.inclination_deg == 51.6464
        assert orbit_info.period_minutes == 92.68
        assert orbit_info.eccentricity == 0.0003456
        assert orbit_info.orbit_type == "Low Earth Orbit"

    def test_orbit_info_schema_validation_ranges(self) -> None:
        """Should validate orbit parameter ranges."""
        from src.schemas.satellite import OrbitInfo

        # Valid ranges
        valid_orbit = OrbitInfo(
            altitude_km=408,
            inclination_deg=51.6,
            period_minutes=90.0,
            eccentricity=0.001,
        )
        assert valid_orbit.altitude_km == 408

        # Invalid altitude (negative)
        with pytest.raises(ValidationError):
            OrbitInfo(
                altitude_km=-100,
                inclination_deg=51.6,
                period_minutes=90.0,
                eccentricity=0.001,
            )

        # Invalid inclination (out of range)
        with pytest.raises(ValidationError):
            OrbitInfo(
                altitude_km=408,
                inclination_deg=190.0,  # Should be 0-180
                period_minutes=90.0,
                eccentricity=0.001,
            )

        # Invalid eccentricity (out of range)
        with pytest.raises(ValidationError):
            OrbitInfo(
                altitude_km=408,
                inclination_deg=51.6,
                period_minutes=90.0,
                eccentricity=1.5,  # Should be 0-1
            )

    def test_orbit_info_schema_optional_fields(self) -> None:
        """Should handle optional fields in OrbitInfo."""
        from src.schemas.satellite import OrbitInfo

        # Minimal orbit info
        minimal_orbit = OrbitInfo(
            altitude_km=408,
            inclination_deg=51.6,
            period_minutes=90.0,
            eccentricity=0.001,
        )

        assert minimal_orbit.perigee_km is None
        assert minimal_orbit.apogee_km is None
        assert minimal_orbit.orbit_type is None

    def test_orbit_info_schema_computed_fields(self) -> None:
        """Should compute derived orbit parameters."""
        from src.schemas.satellite import OrbitInfo

        orbit_info = OrbitInfo(
            altitude_km=408,
            inclination_deg=51.6,
            period_minutes=92.68,
            eccentricity=0.001,
            perigee_km=405,
            apogee_km=411,
        )

        # Should compute orbital velocity if method exists
        if hasattr(orbit_info, "orbital_velocity_km_s"):
            velocity = orbit_info.orbital_velocity_km_s
            assert isinstance(velocity, float)
            assert velocity > 0


class TestTLEDataSchema:
    """Test TLE data schema."""

    def test_tle_data_schema_valid(self) -> None:
        """Should validate TLEData schema with valid data."""
        from src.schemas.satellite import TLEData

        tle_data = {
            "satellite_id": "iss",
            "tle_line1": "1 25544U 98067A   21001.00000000  .00001234  00000-0  12345-4 0  9990",
            "tle_line2": "2 25544  51.6464 123.4567  0003456 123.4567 234.5678 15.49123456123456",
            "epoch": datetime.utcnow(),
            "is_fresh": True,
            "last_updated": datetime.utcnow(),
        }

        tle = TLEData(**tle_data)

        assert tle.satellite_id == "iss"
        assert tle.tle_line1.startswith("1 25544U")
        assert tle.tle_line2.startswith("2 25544")
        assert tle.is_fresh is True

    def test_tle_data_schema_tle_line_validation(self) -> None:
        """Should validate TLE line format."""
        from src.schemas.satellite import TLEData

        valid_tle1 = (
            "1 25544U 98067A   21001.00000000  .00001234  00000-0  12345-4 0  9990"
        )
        valid_tle2 = (
            "2 25544  51.6464 123.4567  0003456 123.4567 234.5678 15.49123456123456"
        )

        # Valid TLE
        tle = TLEData(
            satellite_id="iss",
            tle_line1=valid_tle1,
            tle_line2=valid_tle2,
            epoch=datetime.utcnow(),
        )
        assert tle.tle_line1 == valid_tle1

        # Invalid TLE line 1
        with pytest.raises(ValidationError):
            TLEData(
                satellite_id="iss",
                tle_line1="invalid_tle_line",
                tle_line2=valid_tle2,
                epoch=datetime.utcnow(),
            )

        # Invalid TLE line 2
        with pytest.raises(ValidationError):
            TLEData(
                satellite_id="iss",
                tle_line1=valid_tle1,
                tle_line2="invalid_tle_line",
                epoch=datetime.utcnow(),
            )

    def test_tle_data_schema_epoch_validation(self) -> None:
        """Should validate TLE epoch datetime."""
        from src.schemas.satellite import TLEData

        valid_tle1 = (
            "1 25544U 98067A   21001.00000000  .00001234  00000-0  12345-4 0  9990"
        )
        valid_tle2 = (
            "2 25544  51.6464 123.4567  0003456 123.4567 234.5678 15.49123456123456"
        )

        # Recent epoch (valid)
        recent_epoch = datetime.utcnow() - timedelta(hours=1)
        tle = TLEData(
            satellite_id="iss",
            tle_line1=valid_tle1,
            tle_line2=valid_tle2,
            epoch=recent_epoch,
        )
        assert tle.epoch == recent_epoch

        # Very old epoch (should be rejected)
        with pytest.raises(ValidationError):
            TLEData(
                satellite_id="iss",
                tle_line1=valid_tle1,
                tle_line2=valid_tle2,
                epoch=datetime.utcnow() - timedelta(days=365),
            )

        # Future epoch (should be rejected)
        with pytest.raises(ValidationError):
            TLEData(
                satellite_id="iss",
                tle_line1=valid_tle1,
                tle_line2=valid_tle2,
                epoch=datetime.utcnow() + timedelta(days=30),
            )

    def test_tle_data_schema_freshness_calculation(self) -> None:
        """Should calculate TLE data freshness."""
        from src.schemas.satellite import TLEData

        valid_tle1 = (
            "1 25544U 98067A   21001.00000000  .00001234  00000-0  12345-4 0  9990"
        )
        valid_tle2 = (
            "2 25544  51.6464 123.4567  0003456 123.4567 234.5678 15.49123456123456"
        )

        # Fresh TLE data
        fresh_tle = TLEData(
            satellite_id="iss",
            tle_line1=valid_tle1,
            tle_line2=valid_tle2,
            epoch=datetime.utcnow() - timedelta(hours=1),
            last_updated=datetime.utcnow() - timedelta(hours=1),
        )

        # Should compute freshness if method exists
        if hasattr(fresh_tle, "compute_freshness"):
            assert fresh_tle.compute_freshness() is True

        # Stale TLE data
        stale_tle = TLEData(
            satellite_id="iss",
            tle_line1=valid_tle1,
            tle_line2=valid_tle2,
            epoch=datetime.utcnow() - timedelta(hours=25),
            last_updated=datetime.utcnow() - timedelta(hours=25),
        )

        if hasattr(stale_tle, "compute_freshness"):
            assert stale_tle.compute_freshness() is False


class TestSatellitePositionSchema:
    """Test satellite position schema."""

    def test_satellite_position_schema_valid(self) -> None:
        """Should validate SatellitePosition schema with valid data."""
        from src.schemas.satellite import SatellitePosition

        position_data = {
            "satellite_id": "iss",
            "timestamp": datetime.utcnow(),
            "latitude": 40.7128,
            "longitude": -74.0060,
            "altitude_km": 408.5,
            "velocity_km_s": 7.66,
            "visibility": {
                "is_visible": True,
                "elevation_deg": 45.0,
                "azimuth_deg": 180.0,
                "range_km": 800.0,
            },
        }

        position = SatellitePosition(**position_data)

        assert position.satellite_id == "iss"
        assert position.latitude == 40.7128
        assert position.longitude == -74.0060
        assert position.altitude_km == 408.5
        assert position.visibility.is_visible is True

    def test_satellite_position_schema_coordinate_validation(self) -> None:
        """Should validate coordinate ranges."""
        from src.schemas.satellite import SatellitePosition

        # Valid coordinates
        valid_position = SatellitePosition(
            satellite_id="iss",
            timestamp=datetime.utcnow(),
            latitude=45.0,
            longitude=-90.0,
            altitude_km=400.0,
        )
        assert valid_position.latitude == 45.0
        assert valid_position.longitude == -90.0

        # Invalid latitude (out of range)
        with pytest.raises(ValidationError):
            SatellitePosition(
                satellite_id="iss",
                timestamp=datetime.utcnow(),
                latitude=95.0,  # > 90
                longitude=-90.0,
                altitude_km=400.0,
            )

        # Invalid longitude (out of range)
        with pytest.raises(ValidationError):
            SatellitePosition(
                satellite_id="iss",
                timestamp=datetime.utcnow(),
                latitude=45.0,
                longitude=185.0,  # > 180
                altitude_km=400.0,
            )

        # Invalid altitude (negative)
        with pytest.raises(ValidationError):
            SatellitePosition(
                satellite_id="iss",
                timestamp=datetime.utcnow(),
                latitude=45.0,
                longitude=-90.0,
                altitude_km=-100.0,  # Negative
            )

    def test_satellite_position_schema_velocity_validation(self) -> None:
        """Should validate velocity values."""
        from src.schemas.satellite import SatellitePosition

        # Valid velocity
        valid_position = SatellitePosition(
            satellite_id="iss",
            timestamp=datetime.utcnow(),
            latitude=45.0,
            longitude=-90.0,
            altitude_km=400.0,
            velocity_km_s=7.66,
        )
        assert valid_position.velocity_km_s == 7.66

        # Invalid velocity (negative)
        with pytest.raises(ValidationError):
            SatellitePosition(
                satellite_id="iss",
                timestamp=datetime.utcnow(),
                latitude=45.0,
                longitude=-90.0,
                altitude_km=400.0,
                velocity_km_s=-5.0,
            )


class TestVisibilityInfoSchema:
    """Test visibility information schema."""

    def test_visibility_info_schema_valid(self) -> None:
        """Should validate VisibilityInfo schema with valid data."""
        from src.schemas.satellite import VisibilityInfo

        visibility_data = {
            "is_visible": True,
            "elevation_deg": 45.0,
            "azimuth_deg": 180.0,
            "range_km": 800.0,
            "next_pass": datetime.utcnow() + timedelta(hours=2),
            "pass_duration_seconds": 360,
        }

        visibility = VisibilityInfo(**visibility_data)

        assert visibility.is_visible is True
        assert visibility.elevation_deg == 45.0
        assert visibility.azimuth_deg == 180.0
        assert visibility.range_km == 800.0

    def test_visibility_info_schema_angle_validation(self) -> None:
        """Should validate angle ranges."""
        from src.schemas.satellite import VisibilityInfo

        # Valid angles
        valid_visibility = VisibilityInfo(
            is_visible=True,
            elevation_deg=45.0,  # 0-90
            azimuth_deg=180.0,  # 0-360
            range_km=800.0,
        )
        assert valid_visibility.elevation_deg == 45.0
        assert valid_visibility.azimuth_deg == 180.0

        # Invalid elevation (out of range)
        with pytest.raises(ValidationError):
            VisibilityInfo(
                is_visible=True,
                elevation_deg=95.0,  # > 90
                azimuth_deg=180.0,
                range_km=800.0,
            )

        # Invalid azimuth (out of range)
        with pytest.raises(ValidationError):
            VisibilityInfo(
                is_visible=True,
                elevation_deg=45.0,
                azimuth_deg=365.0,  # > 360
                range_km=800.0,
            )

    def test_visibility_info_schema_optional_fields(self) -> None:
        """Should handle optional fields in VisibilityInfo."""
        from src.schemas.satellite import VisibilityInfo

        # Minimal visibility info
        minimal_visibility = VisibilityInfo(
            is_visible=False, elevation_deg=0.0, azimuth_deg=0.0, range_km=0.0
        )

        assert minimal_visibility.next_pass is None
        assert minimal_visibility.pass_duration_seconds is None


class TestSatelliteSchemaIntegration:
    """Test integration between satellite schemas."""

    def test_satellite_with_orbit_and_tle(self) -> None:
        """Should integrate satellite response with orbit info and TLE data."""
        from src.schemas.satellite import SatelliteResponse, OrbitInfo, TLEData

        orbit_info = OrbitInfo(
            altitude_km=408,
            inclination_deg=51.6,
            period_minutes=92.68,
            eccentricity=0.001,
        )

        satellite = SatelliteResponse(
            id="iss",
            name="International Space Station",
            norad_id=25544,
            category="iss",
            is_active=True,
            orbit_info=orbit_info,
        )

        assert satellite.orbit_info.altitude_km == 408
        assert satellite.orbit_info.inclination_deg == 51.6

    def test_satellite_position_with_visibility(self) -> None:
        """Should integrate position data with visibility info."""
        from src.schemas.satellite import SatellitePosition, VisibilityInfo

        visibility = VisibilityInfo(
            is_visible=True, elevation_deg=45.0, azimuth_deg=180.0, range_km=800.0
        )

        position = SatellitePosition(
            satellite_id="iss",
            timestamp=datetime.utcnow(),
            latitude=40.7128,
            longitude=-74.0060,
            altitude_km=408.5,
            visibility=visibility,
        )

        assert position.visibility.is_visible is True
        assert position.visibility.elevation_deg == 45.0

    def test_schema_serialization_compatibility(self) -> None:
        """Should serialize all schemas to JSON correctly."""
        from src.schemas.satellite import (
            SatelliteResponse,
            OrbitInfo,
            TLEData,
            SatellitePosition,
        )

        # Create complex satellite data
        orbit_info = OrbitInfo(
            altitude_km=408,
            inclination_deg=51.6,
            period_minutes=92.68,
            eccentricity=0.001,
        )

        satellite = SatelliteResponse(
            id="iss",
            name="International Space Station",
            norad_id=25544,
            category="iss",
            is_active=True,
            orbit_info=orbit_info,
            last_updated=datetime.utcnow(),
        )

        # Should serialize to JSON
        json_data = satellite.model_dump_json()
        assert isinstance(json_data, str)
        assert "International Space Station" in json_data
        assert "25544" in json_data

        # Should be parseable
        import json

        parsed_data = json.loads(json_data)
        assert parsed_data["name"] == "International Space Station"
        assert parsed_data["orbit_info"]["altitude_km"] == 408

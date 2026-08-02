"""Test cases for satellite database model."""

from unittest.mock import patch
from datetime import datetime, timedelta
import pytest


class TestSatelliteModel:
    """Test Satellite database model."""

    def test_satellite_model_creation(self) -> None:
        """Should create satellite model with valid data."""
        from src.models.satellite import Satellite

        satellite_data = {
            "id": 1,
            "name": "International Space Station",
            "norad_id": 25544,
            "category": "iss",
            "tle_line1": "1 25544U 98067A   21001.00000000  .00001234  00000-0  12345-4 0  9990",
            "tle_line2": "2 25544  51.6464 123.4567  0003456 123.4567 234.5678 15.49123456123456",
            "tle_epoch": datetime.utcnow(),
            "is_active": True,
            "last_updated": datetime.utcnow(),
        }

        satellite = Satellite(**satellite_data)

        assert satellite.name == "International Space Station"
        assert satellite.norad_id == 25544
        assert satellite.category == "iss"
        assert satellite.is_active is True

    def test_satellite_model_validation(self) -> None:
        """Should validate satellite model fields."""
        from src.models.satellite import Satellite

        # Test valid categories
        valid_categories = ["iss", "weather", "starlink", "remote_sensing"]

        for category in valid_categories:
            satellite = Satellite(
                name="Test Satellite",
                norad_id=12345,
                category=category,
                tle_line1="valid_tle_line1",
                tle_line2="valid_tle_line2",
                tle_epoch=datetime.utcnow(),
                is_active=True,
                last_updated=datetime.utcnow(),
            )
            assert satellite.category == category

        # Test invalid category
        with pytest.raises((ValueError, TypeError)):
            Satellite(
                name="Test Satellite",
                norad_id=12345,
                category="invalid_category",
                tle_line1="valid_tle_line1",
                tle_line2="valid_tle_line2",
                tle_epoch=datetime.utcnow(),
                is_active=True,
                last_updated=datetime.utcnow(),
            )

    def test_satellite_tle_validation(self) -> None:
        """Should validate TLE format."""
        from src.models.satellite import Satellite

        # Test valid TLE lines
        valid_tle1 = (
            "1 25544U 98067A   21001.00000000  .00001234  00000-0  12345-4 0  9990"
        )
        valid_tle2 = (
            "2 25544  51.6464 123.4567  0003456 123.4567 234.5678 15.49123456123456"
        )

        satellite = Satellite(
            name="ISS",
            norad_id=25544,
            category="iss",
            tle_line1=valid_tle1,
            tle_line2=valid_tle2,
            tle_epoch=datetime.utcnow(),
            is_active=True,
            last_updated=datetime.utcnow(),
        )

        assert satellite.tle_line1 == valid_tle1
        assert satellite.tle_line2 == valid_tle2

        # Test invalid TLE lines
        invalid_tle_lines = [
            "",  # Empty string
            "invalid_tle",  # Wrong format
            "1 25544U 98067A",  # Too short
            "2 25544  51.6464 123.4567  0003456 123.4567 234.5678 15.49123456123456 extra",  # Too long
        ]

        for invalid_tle in invalid_tle_lines:
            with pytest.raises((ValueError, TypeError)):
                Satellite(
                    name="Test",
                    norad_id=25544,
                    category="iss",
                    tle_line1=invalid_tle,
                    tle_line2=valid_tle2,
                    tle_epoch=datetime.utcnow(),
                    is_active=True,
                    last_updated=datetime.utcnow(),
                )

    def test_satellite_norad_id_validation(self) -> None:
        """Should validate NORAD ID format."""
        from src.models.satellite import Satellite

        # Test valid NORAD IDs
        valid_norad_ids = [25544, 33591, 44713, 12345]

        for norad_id in valid_norad_ids:
            satellite = Satellite(
                name="Test Satellite",
                norad_id=norad_id,
                category="iss",
                tle_line1="1 25544U 98067A   21001.00000000  .00001234  00000-0  12345-4 0  9990",
                tle_line2="2 25544  51.6464 123.4567  0003456 123.4567 234.5678 15.49123456123456",
                tle_epoch=datetime.utcnow(),
                is_active=True,
                last_updated=datetime.utcnow(),
            )
            assert satellite.norad_id == norad_id

        # Test invalid NORAD IDs
        invalid_norad_ids = [-1, 0, "invalid", None]

        for invalid_id in invalid_norad_ids:
            with pytest.raises((ValueError, TypeError)):
                Satellite(
                    name="Test Satellite",
                    norad_id=invalid_id,
                    category="iss",
                    tle_line1="valid_tle1",
                    tle_line2="valid_tle2",
                    tle_epoch=datetime.utcnow(),
                    is_active=True,
                    last_updated=datetime.utcnow(),
                )

    def test_satellite_name_validation(self) -> None:
        """Should validate satellite name."""
        from src.models.satellite import Satellite

        # Test valid names
        valid_names = [
            "International Space Station",
            "NOAA 19",
            "Terra",
            "Starlink-1234",
            "GOES-16",
        ]

        for name in valid_names:
            satellite = Satellite(
                name=name,
                norad_id=25544,
                category="iss",
                tle_line1="valid_tle1",
                tle_line2="valid_tle2",
                tle_epoch=datetime.utcnow(),
                is_active=True,
                last_updated=datetime.utcnow(),
            )
            assert satellite.name == name

        # Test invalid names
        invalid_names = [
            "",
            None,
            "   ",
            "a" * 1000,
        ]  # Empty, None, whitespace, too long

        for invalid_name in invalid_names:
            with pytest.raises((ValueError, TypeError)):
                Satellite(
                    name=invalid_name,
                    norad_id=25544,
                    category="iss",
                    tle_line1="valid_tle1",
                    tle_line2="valid_tle2",
                    tle_epoch=datetime.utcnow(),
                    is_active=True,
                    last_updated=datetime.utcnow(),
                )

    def test_satellite_string_representation(self) -> None:
        """Should provide meaningful string representation."""
        from src.models.satellite import Satellite

        satellite = Satellite(
            name="International Space Station",
            norad_id=25544,
            category="iss",
            tle_line1="valid_tle1",
            tle_line2="valid_tle2",
            tle_epoch=datetime.utcnow(),
            is_active=True,
            last_updated=datetime.utcnow(),
        )

        str_repr = str(satellite)
        assert "International Space Station" in str_repr
        assert "25544" in str_repr

    def test_satellite_dictionary_conversion(self) -> None:
        """Should convert to dictionary format."""
        from src.models.satellite import Satellite

        now = datetime.utcnow()
        satellite = Satellite(
            name="International Space Station",
            norad_id=25544,
            category="iss",
            tle_line1="valid_tle1",
            tle_line2="valid_tle2",
            tle_epoch=now,
            is_active=True,
            last_updated=now,
        )

        satellite_dict = satellite.to_dict()

        assert satellite_dict["name"] == "International Space Station"
        assert satellite_dict["norad_id"] == 25544
        assert satellite_dict["category"] == "iss"
        assert satellite_dict["is_active"] is True
        assert isinstance(satellite_dict["tle_epoch"], datetime)


class TestSatelliteDatabaseOperations:
    """Test satellite database operations."""

    def test_create_satellite_in_database(self) -> None:
        """Should create satellite record in database."""
        from src.models.satellite import Satellite

        with patch("src.database.Database.execute_query") as mock_execute:
            satellite_data = {
                "name": "Test Satellite",
                "norad_id": 12345,
                "category": "weather",
                "tle_line1": "valid_tle1",
                "tle_line2": "valid_tle2",
                "tle_epoch": datetime.utcnow(),
                "is_active": True,
                "last_updated": datetime.utcnow(),
            }

            satellite = Satellite(**satellite_data)
            satellite.save()

            mock_execute.assert_called_once()
            # Verify INSERT SQL was called
            sql_call = mock_execute.call_args[0][0]
            assert "INSERT" in sql_call.upper()
            assert "satellites" in sql_call.lower()

    def test_update_satellite_in_database(self) -> None:
        """Should update existing satellite record."""
        from src.models.satellite import Satellite

        with patch("src.database.Database.execute_query") as mock_execute:
            satellite = Satellite(
                id=1,
                name="Updated Satellite",
                norad_id=12345,
                category="weather",
                tle_line1="updated_tle1",
                tle_line2="updated_tle2",
                tle_epoch=datetime.utcnow(),
                is_active=False,
                last_updated=datetime.utcnow(),
            )

            satellite.save()

            mock_execute.assert_called_once()
            # Verify UPDATE SQL was called
            sql_call = mock_execute.call_args[0][0]
            assert "UPDATE" in sql_call.upper()
            assert "satellites" in sql_call.lower()

    def test_delete_satellite_from_database(self) -> None:
        """Should delete satellite record from database."""
        from src.models.satellite import Satellite

        with patch("src.database.Database.execute_query") as mock_execute:
            satellite = Satellite(
                id=1,
                name="To Delete",
                norad_id=12345,
                category="weather",
                tle_line1="tle1",
                tle_line2="tle2",
                tle_epoch=datetime.utcnow(),
                is_active=True,
                last_updated=datetime.utcnow(),
            )

            satellite.delete()

            mock_execute.assert_called_once()
            # Verify DELETE SQL was called
            sql_call = mock_execute.call_args[0][0]
            assert "DELETE" in sql_call.upper()
            assert "satellites" in sql_call.lower()

    def test_find_satellite_by_id(self) -> None:
        """Should find satellite by ID."""
        from src.models.satellite import Satellite

        mock_result = {
            "id": 1,
            "name": "International Space Station",
            "norad_id": 25544,
            "category": "iss",
            "tle_line1": "tle1",
            "tle_line2": "tle2",
            "tle_epoch": datetime.utcnow(),
            "is_active": True,
            "last_updated": datetime.utcnow(),
        }

        with patch(
            "src.database.Database.fetch_one", return_value=mock_result
        ) as mock_fetch:
            satellite = Satellite.find_by_id(1)

            assert satellite is not None
            assert satellite.id == 1
            assert satellite.name == "International Space Station"
            assert satellite.norad_id == 25544

            mock_fetch.assert_called_once()

    def test_find_satellite_by_norad_id(self) -> None:
        """Should find satellite by NORAD ID."""
        from src.models.satellite import Satellite

        mock_result = {
            "id": 1,
            "name": "International Space Station",
            "norad_id": 25544,
            "category": "iss",
            "tle_line1": "tle1",
            "tle_line2": "tle2",
            "tle_epoch": datetime.utcnow(),
            "is_active": True,
            "last_updated": datetime.utcnow(),
        }

        with patch(
            "src.database.Database.fetch_one", return_value=mock_result
        ) as mock_fetch:
            satellite = Satellite.find_by_norad_id(25544)

            assert satellite is not None
            assert satellite.norad_id == 25544
            assert satellite.name == "International Space Station"

            mock_fetch.assert_called_once()

    def test_find_satellites_by_category(self) -> None:
        """Should find satellites by category."""
        from src.models.satellite import Satellite

        mock_results = [
            {
                "id": 1,
                "name": "NOAA 19",
                "norad_id": 33591,
                "category": "weather",
                "tle_line1": "tle1",
                "tle_line2": "tle2",
                "tle_epoch": datetime.utcnow(),
                "is_active": True,
                "last_updated": datetime.utcnow(),
            },
            {
                "id": 2,
                "name": "GOES-16",
                "norad_id": 41866,
                "category": "weather",
                "tle_line1": "tle1",
                "tle_line2": "tle2",
                "tle_epoch": datetime.utcnow(),
                "is_active": True,
                "last_updated": datetime.utcnow(),
            },
        ]

        with patch(
            "src.database.Database.fetch_all", return_value=mock_results
        ) as mock_fetch:
            satellites = Satellite.find_by_category("weather")

            assert len(satellites) == 2
            assert all(sat.category == "weather" for sat in satellites)
            assert satellites[0].name == "NOAA 19"
            assert satellites[1].name == "GOES-16"

            mock_fetch.assert_called_once()

    def test_find_active_satellites(self) -> None:
        """Should find only active satellites."""
        from src.models.satellite import Satellite

        mock_results = [
            {
                "id": 1,
                "name": "Active Satellite",
                "norad_id": 12345,
                "category": "iss",
                "tle_line1": "tle1",
                "tle_line2": "tle2",
                "tle_epoch": datetime.utcnow(),
                "is_active": True,
                "last_updated": datetime.utcnow(),
            }
        ]

        with patch(
            "src.database.Database.fetch_all", return_value=mock_results
        ) as mock_fetch:
            active_satellites = Satellite.find_active()

            assert len(active_satellites) == 1
            assert all(sat.is_active for sat in active_satellites)

            mock_fetch.assert_called_once()
            # Verify WHERE is_active = True clause
            sql_call = mock_fetch.call_args[0][0]
            assert "is_active" in sql_call.lower()


class TestSatelliteTLEManagement:
    """Test TLE data management in satellite model."""

    def test_update_tle_data(self) -> None:
        """Should update TLE data for satellite."""
        from src.models.satellite import Satellite

        satellite = Satellite(
            id=1,
            name="Test Satellite",
            norad_id=25544,
            category="iss",
            tle_line1="old_tle1",
            tle_line2="old_tle2",
            tle_epoch=datetime.utcnow() - timedelta(days=1),
            is_active=True,
            last_updated=datetime.utcnow() - timedelta(days=1),
        )

        new_tle_data = {
            "tle_line1": "new_tle1",
            "tle_line2": "new_tle2",
            "tle_epoch": datetime.utcnow(),
        }

        with patch.object(satellite, "save") as mock_save:
            satellite.update_tle_data(new_tle_data)

            assert satellite.tle_line1 == "new_tle1"
            assert satellite.tle_line2 == "new_tle2"
            assert satellite.tle_epoch == new_tle_data["tle_epoch"]
            assert satellite.last_updated is not None

            mock_save.assert_called_once()

    def test_is_tle_data_fresh(self) -> None:
        """Should check if TLE data is fresh."""
        from src.models.satellite import Satellite

        # Fresh TLE data
        fresh_satellite = Satellite(
            name="Fresh Satellite",
            norad_id=25544,
            category="iss",
            tle_line1="tle1",
            tle_line2="tle2",
            tle_epoch=datetime.utcnow() - timedelta(hours=1),
            is_active=True,
            last_updated=datetime.utcnow() - timedelta(hours=1),
        )

        assert fresh_satellite.is_tle_data_fresh(max_age_hours=6) is True

        # Stale TLE data
        stale_satellite = Satellite(
            name="Stale Satellite",
            norad_id=25544,
            category="iss",
            tle_line1="tle1",
            tle_line2="tle2",
            tle_epoch=datetime.utcnow() - timedelta(hours=25),
            is_active=True,
            last_updated=datetime.utcnow() - timedelta(hours=25),
        )

        assert stale_satellite.is_tle_data_fresh(max_age_hours=6) is False

    def test_tle_epoch_validation(self) -> None:
        """Should validate TLE epoch is reasonable."""
        from src.models.satellite import Satellite

        # Valid epoch (recent)
        valid_epoch = datetime.utcnow() - timedelta(days=1)
        satellite = Satellite(
            name="Test",
            norad_id=25544,
            category="iss",
            tle_line1="tle1",
            tle_line2="tle2",
            tle_epoch=valid_epoch,
            is_active=True,
            last_updated=datetime.utcnow(),
        )
        assert satellite.tle_epoch == valid_epoch

        # Invalid epoch (too old)
        with pytest.raises((ValueError, TypeError)):
            Satellite(
                name="Test",
                norad_id=25544,
                category="iss",
                tle_line1="tle1",
                tle_line2="tle2",
                tle_epoch=datetime.utcnow() - timedelta(days=365),  # Too old
                is_active=True,
                last_updated=datetime.utcnow(),
            )

        # Invalid epoch (future)
        with pytest.raises((ValueError, TypeError)):
            Satellite(
                name="Test",
                norad_id=25544,
                category="iss",
                tle_line1="tle1",
                tle_line2="tle2",
                tle_epoch=datetime.utcnow() + timedelta(days=30),  # Future
                is_active=True,
                last_updated=datetime.utcnow(),
            )


class TestSatelliteUtilityMethods:
    """Test utility methods of satellite model."""

    def test_satellite_equality(self) -> None:
        """Should compare satellites correctly."""
        from src.models.satellite import Satellite

        satellite1 = Satellite(
            id=1,
            name="Test Satellite",
            norad_id=25544,
            category="iss",
            tle_line1="tle1",
            tle_line2="tle2",
            tle_epoch=datetime.utcnow(),
            is_active=True,
            last_updated=datetime.utcnow(),
        )

        satellite2 = Satellite(
            id=1,
            name="Test Satellite",
            norad_id=25544,
            category="iss",
            tle_line1="tle1",
            tle_line2="tle2",
            tle_epoch=datetime.utcnow(),
            is_active=True,
            last_updated=datetime.utcnow(),
        )

        satellite3 = Satellite(
            id=2,
            name="Different Satellite",
            norad_id=33591,
            category="weather",
            tle_line1="tle1",
            tle_line2="tle2",
            tle_epoch=datetime.utcnow(),
            is_active=True,
            last_updated=datetime.utcnow(),
        )

        assert satellite1 == satellite2  # Same ID
        assert satellite1 != satellite3  # Different ID

    def test_satellite_hash(self) -> None:
        """Should provide consistent hash for sets/dicts."""
        from src.models.satellite import Satellite

        satellite = Satellite(
            id=1,
            name="Test Satellite",
            norad_id=25544,
            category="iss",
            tle_line1="tle1",
            tle_line2="tle2",
            tle_epoch=datetime.utcnow(),
            is_active=True,
            last_updated=datetime.utcnow(),
        )

        # Should be hashable for use in sets/dicts
        satellite_set = {satellite}
        satellite_dict = {satellite: "test_value"}

        assert len(satellite_set) == 1
        assert satellite in satellite_dict

    def test_satellite_json_serialization(self) -> None:
        """Should serialize to JSON compatible format."""
        from src.models.satellite import Satellite

        now = datetime.utcnow()
        satellite = Satellite(
            id=1,
            name="Test Satellite",
            norad_id=25544,
            category="iss",
            tle_line1="tle1",
            tle_line2="tle2",
            tle_epoch=now,
            is_active=True,
            last_updated=now,
        )

        json_data = satellite.to_json()

        # Should handle datetime serialization
        assert isinstance(json_data, str)

        # Should be parseable back to dict
        import json

        parsed_data = json.loads(json_data)
        assert parsed_data["name"] == "Test Satellite"
        assert parsed_data["norad_id"] == 25544

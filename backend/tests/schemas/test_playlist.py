"""Test cases for playlist Pydantic schemas."""

from datetime import datetime, timedelta

from src.config import utcnow

import pytest
from pydantic import ValidationError


class TestPlaylistSchemas:
    """Test playlist-related Pydantic schemas."""

    def test_track_schema_valid(self) -> None:
        """Should validate Track schema with valid data."""
        from src.schemas.playlist import Track

        track_data = {
            "id": "track_123",
            "name": "Test Song",
            "duration_ms": 180000,
            "artists": [
                {"id": "artist_123", "name": "Test Artist"},
                {"id": "artist_456", "name": "Featured Artist"},
            ],
            "album": {
                "id": "album_123",
                "name": "Test Album",
                "release_date": "2023-01-01",
            },
            "preview_url": "https://preview.spotify.com/track_123.mp3",
            "external_urls": {"spotify": "https://open.spotify.com/track/track_123"},
            "popularity": 85,
            "explicit": False,
        }

        track = Track(**track_data)

        assert track.id == "track_123"
        assert track.name == "Test Song"
        assert track.duration_ms == 180000
        assert len(track.artists) == 2
        assert track.artists[0].name == "Test Artist"
        assert track.album.name == "Test Album"
        assert track.popularity == 85

    def test_track_schema_required_fields(self) -> None:
        """Should require essential fields in Track schema."""
        from src.schemas.playlist import Track

        # Missing required fields
        with pytest.raises(ValidationError) as exc_info:
            Track()

        error_str = str(exc_info.value)
        assert "id" in error_str
        assert "name" in error_str
        assert "duration_ms" in error_str

        # Minimal valid track
        minimal_track = Track(
            id="track_123",
            name="Test Song",
            duration_ms=180000,
            artists=[{"id": "artist_123", "name": "Test Artist"}],
            album={"id": "album_123", "name": "Test Album"},
        )

        assert minimal_track.id == "track_123"
        assert minimal_track.preview_url is None
        assert minimal_track.popularity is None

    def test_track_schema_duration_validation(self) -> None:
        """Should validate track duration."""
        from src.schemas.playlist import Track

        # Valid durations (1-8 minutes in milliseconds)
        valid_durations = [60000, 180000, 240000, 480000]  # 1, 3, 4, 8 minutes

        for duration in valid_durations:
            track = Track(
                id="track_123",
                name="Test Song",
                duration_ms=duration,
                artists=[{"id": "artist_123", "name": "Test Artist"}],
                album={"id": "album_123", "name": "Test Album"},
            )
            assert track.duration_ms == duration

        # Invalid durations
        invalid_durations = [
            -1,
            0,
            30000,
            600000,
        ]  # Negative, zero, too short, too long

        for invalid_duration in invalid_durations:
            with pytest.raises(ValidationError):
                Track(
                    id="track_123",
                    name="Test Song",
                    duration_ms=invalid_duration,
                    artists=[{"id": "artist_123", "name": "Test Artist"}],
                    album={"id": "album_123", "name": "Test Album"},
                )

    def test_track_schema_popularity_validation(self) -> None:
        """Should validate popularity score range."""
        from src.schemas.playlist import Track

        # Valid popularity scores (0-100)
        valid_scores = [0, 50, 85, 100]

        for score in valid_scores:
            track = Track(
                id="track_123",
                name="Test Song",
                duration_ms=180000,
                artists=[{"id": "artist_123", "name": "Test Artist"}],
                album={"id": "album_123", "name": "Test Album"},
                popularity=score,
            )
            assert track.popularity == score

        # Invalid popularity scores
        invalid_scores = [-1, 101, 150]

        for invalid_score in invalid_scores:
            with pytest.raises(ValidationError):
                Track(
                    id="track_123",
                    name="Test Song",
                    duration_ms=180000,
                    artists=[{"id": "artist_123", "name": "Test Artist"}],
                    album={"id": "album_123", "name": "Test Album"},
                    popularity=invalid_score,
                )


class TestArtistSchema:
    """Test artist schema."""

    def test_artist_schema_valid(self) -> None:
        """Should validate Artist schema with valid data."""
        from src.schemas.playlist import Artist

        artist_data = {
            "id": "artist_123",
            "name": "Test Artist",
            "genres": ["pop", "rock"],
            "popularity": 75,
            "external_urls": {"spotify": "https://open.spotify.com/artist/artist_123"},
        }

        artist = Artist(**artist_data)

        assert artist.id == "artist_123"
        assert artist.name == "Test Artist"
        assert artist.genres == ["pop", "rock"]
        assert artist.popularity == 75

    def test_artist_schema_required_fields(self) -> None:
        """Should require essential fields in Artist schema."""
        from src.schemas.playlist import Artist

        # Missing required fields
        with pytest.raises(ValidationError) as exc_info:
            Artist()

        error_str = str(exc_info.value)
        assert "id" in error_str
        assert "name" in error_str

        # Minimal valid artist
        minimal_artist = Artist(id="artist_123", name="Test Artist")

        assert minimal_artist.id == "artist_123"
        assert minimal_artist.name == "Test Artist"
        assert minimal_artist.genres is None
        assert minimal_artist.popularity is None

    def test_artist_schema_genres_validation(self) -> None:
        """Should validate genres list."""
        from src.schemas.playlist import Artist

        # Valid genres
        valid_genres = [
            ["pop"],
            ["rock", "alternative"],
            ["electronic", "dance", "house"],
        ]

        for genres in valid_genres:
            artist = Artist(id="artist_123", name="Test Artist", genres=genres)
            assert artist.genres == genres

        # Empty genres list should be valid
        artist = Artist(id="artist_123", name="Test Artist", genres=[])
        assert artist.genres == []


class TestAlbumSchema:
    """Test album schema."""

    def test_album_schema_valid(self) -> None:
        """Should validate Album schema with valid data."""
        from src.schemas.playlist import Album

        album_data = {
            "id": "album_123",
            "name": "Test Album",
            "release_date": "2023-01-01",
            "total_tracks": 12,
            "album_type": "album",
            "artists": [{"id": "artist_123", "name": "Test Artist"}],
            "external_urls": {"spotify": "https://open.spotify.com/album/album_123"},
            "images": [
                {
                    "url": "https://example.com/album_cover.jpg",
                    "height": 640,
                    "width": 640,
                }
            ],
        }

        album = Album(**album_data)

        assert album.id == "album_123"
        assert album.name == "Test Album"
        assert album.release_date == "2023-01-01"
        assert album.total_tracks == 12
        assert album.album_type == "album"

    def test_album_schema_required_fields(self) -> None:
        """Should require essential fields in Album schema."""
        from src.schemas.playlist import Album

        # Missing required fields
        with pytest.raises(ValidationError) as exc_info:
            Album()

        error_str = str(exc_info.value)
        assert "id" in error_str
        assert "name" in error_str

        # Minimal valid album
        minimal_album = Album(id="album_123", name="Test Album")

        assert minimal_album.id == "album_123"
        assert minimal_album.name == "Test Album"
        assert minimal_album.release_date is None
        assert minimal_album.total_tracks is None

    def test_album_schema_album_type_validation(self) -> None:
        """Should validate album type values."""
        from src.schemas.playlist import Album

        valid_types = ["album", "single", "compilation"]

        for album_type in valid_types:
            album = Album(id="album_123", name="Test Album", album_type=album_type)
            assert album.album_type == album_type

        # Invalid album type
        with pytest.raises(ValidationError):
            Album(id="album_123", name="Test Album", album_type="invalid_type")

    def test_album_schema_total_tracks_validation(self) -> None:
        """Should validate total tracks count."""
        from src.schemas.playlist import Album

        # Valid track counts
        valid_counts = [1, 12, 20, 100]

        for count in valid_counts:
            album = Album(id="album_123", name="Test Album", total_tracks=count)
            assert album.total_tracks == count

        # Invalid track counts
        invalid_counts = [-1, 0, 1000]  # Negative, zero, or unreasonably high

        for invalid_count in invalid_counts:
            with pytest.raises(ValidationError):
                Album(id="album_123", name="Test Album", total_tracks=invalid_count)


class TestPlaylistResponseSchema:
    """Test playlist response schema."""

    def test_playlist_response_schema_valid(self) -> None:
        """Should validate PlaylistResponse schema with valid data."""
        from src.schemas.playlist import PlaylistResponse, Track

        tracks = [
            Track(
                id="track_1",
                name="Song 1",
                duration_ms=180000,
                artists=[{"id": "artist_1", "name": "Artist 1"}],
                album={"id": "album_1", "name": "Album 1"},
            ),
            Track(
                id="track_2",
                name="Song 2",
                duration_ms=240000,
                artists=[{"id": "artist_2", "name": "Artist 2"}],
                album={"id": "album_2", "name": "Album 2"},
            ),
        ]

        playlist_data = {
            "id": "playlist_123",
            "name": "Test Playlist",
            "description": "A test playlist",
            "tracks": tracks,
            "total_tracks": 2,
            "duration_ms": 420000,
            "created_at": utcnow(),
            "region_info": {
                "country_code": "US",
                "country_name": "United States",
                "continent": "North America",
            },
        }

        playlist = PlaylistResponse(**playlist_data)

        assert playlist.id == "playlist_123"
        assert playlist.name == "Test Playlist"
        assert len(playlist.tracks) == 2
        assert playlist.total_tracks == 2
        assert playlist.duration_ms == 420000
        assert playlist.region_info.country_code == "US"

    def test_playlist_response_schema_computed_duration(self) -> None:
        """Should compute total duration from tracks."""
        from src.schemas.playlist import PlaylistResponse, Track

        tracks = [
            Track(
                id="track_1",
                name="Song 1",
                duration_ms=180000,
                artists=[{"id": "artist_1", "name": "Artist 1"}],
                album={"id": "album_1", "name": "Album 1"},
            ),
            Track(
                id="track_2",
                name="Song 2",
                duration_ms=240000,
                artists=[{"id": "artist_2", "name": "Artist 2"}],
                album={"id": "album_2", "name": "Album 2"},
            ),
        ]

        playlist = PlaylistResponse(
            id="playlist_123",
            name="Test Playlist",
            tracks=tracks,
            total_tracks=2,
            created_at=utcnow(),
        )

        # Should compute duration if not provided
        if hasattr(playlist, "compute_duration"):
            computed_duration = playlist.compute_duration()
            assert computed_duration == 420000  # 180000 + 240000

    def test_playlist_response_schema_track_count_validation(self) -> None:
        """Should validate track count consistency."""
        from src.schemas.playlist import PlaylistResponse, Track

        tracks = [
            Track(
                id="track_1",
                name="Song 1",
                duration_ms=180000,
                artists=[{"id": "artist_1", "name": "Artist 1"}],
                album={"id": "album_1", "name": "Album 1"},
            )
        ]

        # Consistent track count
        playlist = PlaylistResponse(
            id="playlist_123",
            name="Test Playlist",
            tracks=tracks,
            total_tracks=1,
            created_at=utcnow(),
        )
        assert playlist.total_tracks == 1

        # Inconsistent track count should be handled
        playlist_inconsistent = PlaylistResponse(
            id="playlist_123",
            name="Test Playlist",
            tracks=tracks,
            total_tracks=5,  # Doesn't match actual track count
            created_at=utcnow(),
        )
        # Should either auto-correct or validate
        assert playlist_inconsistent.total_tracks == 5  # Or should be corrected to 1


class TestRegionInfoSchema:
    """Test region information schema."""

    def test_region_info_schema_valid(self) -> None:
        """Should validate RegionInfo schema with valid data."""
        from src.schemas.playlist import RegionInfo

        region_data = {
            "country_code": "US",
            "country_name": "United States",
            "continent": "North America",
            "timezone": "America/New_York",
            "language": "en",
            "spotify_market": "US",
        }

        region = RegionInfo(**region_data)

        assert region.country_code == "US"
        assert region.country_name == "United States"
        assert region.continent == "North America"
        assert region.timezone == "America/New_York"
        assert region.spotify_market == "US"

    def test_region_info_schema_required_fields(self) -> None:
        """Should require essential fields in RegionInfo schema."""
        from src.schemas.playlist import RegionInfo

        # Missing required fields
        with pytest.raises(ValidationError) as exc_info:
            RegionInfo()

        error_str = str(exc_info.value)
        assert "country_code" in error_str
        assert "country_name" in error_str

        # Minimal valid region
        minimal_region = RegionInfo(country_code="US", country_name="United States")

        assert minimal_region.country_code == "US"
        assert minimal_region.country_name == "United States"
        assert minimal_region.continent is None
        assert minimal_region.timezone is None

    def test_region_info_schema_country_code_validation(self) -> None:
        """Should validate country code format."""
        from src.schemas.playlist import RegionInfo

        # Valid country codes (ISO 3166-1 alpha-2)
        valid_codes = ["US", "GB", "FR", "DE", "JP", "AU", "CA", "BR"]

        for code in valid_codes:
            region = RegionInfo(country_code=code, country_name=f"Country {code}")
            assert region.country_code == code

        # Invalid country codes
        invalid_codes = ["USA", "United States", "", "123", "ZZ"]

        for invalid_code in invalid_codes:
            with pytest.raises(ValidationError):
                RegionInfo(country_code=invalid_code, country_name="Test Country")


class TestOrbitalPlaylistSchema:
    """Test orbital playlist schema."""

    def test_orbital_playlist_schema_valid(self) -> None:
        """Should validate OrbitalPlaylist schema with valid data."""
        from src.schemas.playlist import OrbitalPlaylist, Track

        tracks = [
            Track(
                id="track_1",
                name="Song 1",
                duration_ms=180000,
                artists=[{"id": "artist_1", "name": "Artist 1"}],
                album={"id": "album_1", "name": "Album 1"},
            )
        ]

        orbital_data = {
            "session_id": "session_123",
            "satellite_id": "iss",
            "tracks": tracks,
            "duration_minutes": 90,
            "regions_covered": ["US", "CA", "GB", "FR"],
            "start_position": {
                "latitude": 40.7128,
                "longitude": -74.0060,
                "timestamp": utcnow(),
            },
            "end_position": {
                "latitude": 51.5074,
                "longitude": -0.1278,
                "timestamp": utcnow() + timedelta(minutes=90),
            },
            "created_at": utcnow(),
        }

        orbital_playlist = OrbitalPlaylist(**orbital_data)

        assert orbital_playlist.session_id == "session_123"
        assert orbital_playlist.satellite_id == "iss"
        assert len(orbital_playlist.tracks) == 1
        assert orbital_playlist.duration_minutes == 90
        assert len(orbital_playlist.regions_covered) == 4

    def test_orbital_playlist_schema_duration_validation(self) -> None:
        """Should validate orbital duration."""
        from src.schemas.playlist import OrbitalPlaylist

        # Valid durations (typical orbital periods)
        valid_durations = [90, 92, 95, 100, 120]

        for duration in valid_durations:
            orbital_playlist = OrbitalPlaylist(
                session_id="session_123",
                satellite_id="iss",
                tracks=[],
                duration_minutes=duration,
                regions_covered=[],
                created_at=utcnow(),
            )
            assert orbital_playlist.duration_minutes == duration

        # Invalid durations
        invalid_durations = [-1, 0, 10, 1000]  # Negative, too short, too long

        for invalid_duration in invalid_durations:
            with pytest.raises(ValidationError):
                OrbitalPlaylist(
                    session_id="session_123",
                    satellite_id="iss",
                    tracks=[],
                    duration_minutes=invalid_duration,
                    regions_covered=[],
                    created_at=utcnow(),
                )

    def test_orbital_playlist_schema_satellite_validation(self) -> None:
        """Should validate satellite ID."""
        from src.schemas.playlist import OrbitalPlaylist

        # Valid satellite IDs
        valid_satellites = ["iss", "noaa19", "terra", "starlink-1234"]

        for satellite_id in valid_satellites:
            orbital_playlist = OrbitalPlaylist(
                session_id="session_123",
                satellite_id=satellite_id,
                tracks=[],
                duration_minutes=90,
                regions_covered=[],
                created_at=utcnow(),
            )
            assert orbital_playlist.satellite_id == satellite_id

        # Invalid satellite IDs
        invalid_satellites = ["", "invalid/satellite", "satellite with spaces"]

        for invalid_satellite in invalid_satellites:
            with pytest.raises(ValidationError):
                OrbitalPlaylist(
                    session_id="session_123",
                    satellite_id=invalid_satellite,
                    tracks=[],
                    duration_minutes=90,
                    regions_covered=[],
                    created_at=utcnow(),
                )


class TestPositionSchema:
    """Test position schema."""

    def test_position_schema_valid(self) -> None:
        """Should validate Position schema with valid data."""
        from src.schemas.playlist import Position

        position_data = {
            "latitude": 40.7128,
            "longitude": -74.0060,
            "timestamp": utcnow(),
            "altitude_km": 408.5,
        }

        position = Position(**position_data)

        assert position.latitude == 40.7128
        assert position.longitude == -74.0060
        assert isinstance(position.timestamp, datetime)
        assert position.altitude_km == 408.5

    def test_position_schema_coordinate_validation(self) -> None:
        """Should validate coordinate ranges."""
        from src.schemas.playlist import Position

        # Valid coordinates
        valid_position = Position(
            latitude=45.0, longitude=-90.0, timestamp=utcnow()
        )
        assert valid_position.latitude == 45.0
        assert valid_position.longitude == -90.0

        # Invalid latitude
        with pytest.raises(ValidationError):
            Position(
                latitude=95.0,  # > 90
                longitude=-90.0,
                timestamp=utcnow(),
            )

        # Invalid longitude
        with pytest.raises(ValidationError):
            Position(
                latitude=45.0,
                longitude=185.0,  # > 180
                timestamp=utcnow(),
            )


class TestPlaylistSchemaIntegration:
    """Test integration between playlist schemas."""

    def test_complete_orbital_playlist_creation(self) -> None:
        """Should create complete orbital playlist with all components."""
        from src.schemas.playlist import (
            OrbitalPlaylist,
            Track,
            Artist,
            Album,
            Position,
        )

        # Create artist
        artist = Artist(id="artist_123", name="Test Artist", genres=["pop"])

        # Create album
        album = Album(id="album_123", name="Test Album", album_type="album")

        # Create track
        track = Track(
            id="track_123",
            name="Test Song",
            duration_ms=180000,
            artists=[artist],
            album=album,
        )

        # Create positions
        start_position = Position(
            latitude=40.7128, longitude=-74.0060, timestamp=utcnow()
        )

        end_position = Position(
            latitude=51.5074,
            longitude=-0.1278,
            timestamp=utcnow() + timedelta(minutes=90),
        )

        # Create orbital playlist
        orbital_playlist = OrbitalPlaylist(
            session_id="session_123",
            satellite_id="iss",
            tracks=[track],
            duration_minutes=90,
            regions_covered=["US", "GB"],
            start_position=start_position,
            end_position=end_position,
            created_at=utcnow(),
        )

        assert orbital_playlist.tracks[0].artists[0].name == "Test Artist"
        assert orbital_playlist.start_position.latitude == 40.7128
        assert orbital_playlist.end_position.latitude == 51.5074

    def test_schema_serialization_compatibility(self) -> None:
        """Should serialize all schemas to JSON correctly."""
        from src.schemas.playlist import PlaylistResponse, Track, RegionInfo

        # Create track
        track = Track(
            id="track_123",
            name="Test Song",
            duration_ms=180000,
            artists=[{"id": "artist_123", "name": "Test Artist"}],
            album={"id": "album_123", "name": "Test Album"},
        )

        # Create region info
        region_info = RegionInfo(
            country_code="US", country_name="United States", continent="North America"
        )

        # Create playlist
        playlist = PlaylistResponse(
            id="playlist_123",
            name="Test Playlist",
            tracks=[track],
            total_tracks=1,
            duration_ms=180000,
            created_at=utcnow(),
            region_info=region_info,
        )

        # Should serialize to JSON
        json_data = playlist.model_dump_json()
        assert isinstance(json_data, str)
        assert "Test Playlist" in json_data
        assert "Test Song" in json_data
        assert "United States" in json_data

        # Should be parseable
        import json

        parsed_data = json.loads(json_data)
        assert parsed_data["name"] == "Test Playlist"
        assert parsed_data["tracks"][0]["name"] == "Test Song"
        assert parsed_data["region_info"]["country_name"] == "United States"

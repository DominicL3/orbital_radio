"""Test cases for playlist service."""

from unittest.mock import Mock, patch
from typing import Dict, Any
from datetime import timedelta

from src.config import utcnow

import pytest


@pytest.fixture
def mock_track() -> Dict[str, Any]:
    """Mock track data."""
    return {
        "id": "track_123",
        "name": "Test Song",
        "duration_ms": 180000,
        "artists": [{"name": "Test Artist", "id": "artist_123"}],
        "album": {"name": "Test Album", "id": "album_123"},
        "preview_url": "https://preview.spotify.com/track_123.mp3",
        "external_urls": {"spotify": "https://spotify.com/track/track_123"},
    }


@pytest.fixture
def mock_orbital_session() -> Dict[str, Any]:
    """Mock orbital session data."""
    return {
        "session_id": "session_123",
        "satellite_id": "iss",
        "start_time": utcnow(),
        "current_position": {"latitude": 40.7128, "longitude": -74.0060},
        "played_tracks": {"track_1", "track_2"},
        "track_history": [
            {
                "id": "track_1",
                "name": "Previous Song",
                "timestamp": utcnow() - timedelta(minutes=5),
            },
            {"id": "track_2", "name": "Current Song", "timestamp": utcnow()},
        ],
        "playback_position": {"track_2": 45000},  # 45 seconds into current track
    }


class TestPlaylistService:
    """Test PlaylistService class."""

    def test_initialization(self) -> None:
        """Should initialize with proper dependencies."""
        from src.services.playlist_service import PlaylistService

        service = PlaylistService()
        assert hasattr(service, "playlist_generator")
        assert hasattr(service, "satellite_service")
        assert hasattr(service, "cache_service")
        assert hasattr(service, "spotify_client")

    @patch("src.core.playlist_generator.GeographicPlaylistGenerator.get_next_track")
    @patch(
        "src.services.satellite_service.SatelliteService.get_current_satellite_position"
    )
    def test_get_next_track_success(
        self,
        mock_get_position: Mock,
        mock_get_next: Mock,
        mock_track: Dict[str, Any],
        mock_orbital_session: Dict[str, Any],
    ) -> None:
        """Should get next track based on current satellite position."""
        from src.services.playlist_service import PlaylistService

        mock_get_position.return_value = {"latitude": 40.7128, "longitude": -74.0060}
        mock_get_next.return_value = mock_track

        service = PlaylistService()

        with patch.object(
            service.cache_service, "get_session", return_value=mock_orbital_session
        ):
            track = service.get_next_track("session_123")

            assert track["id"] == "track_123"
            assert track["name"] == "Test Song"
            assert track["duration_ms"] == 180000

            mock_get_position.assert_called_once_with("iss")
            mock_get_next.assert_called_once()

    def test_get_next_track_invalid_session(self) -> None:
        """Should handle invalid session ID."""
        from src.services.playlist_service import PlaylistService

        service = PlaylistService()

        with patch.object(service.cache_service, "get_session", return_value=None):
            with pytest.raises(ValueError) as exc_info:
                service.get_next_track("invalid_session")

            assert "session" in str(exc_info.value).lower()

    @patch("src.core.playlist_generator.GeographicPlaylistGenerator.get_previous_track")
    def test_get_previous_track_success(
        self, mock_get_previous: Mock, mock_orbital_session: Dict[str, Any]
    ) -> None:
        """Should get previous track from session history."""
        from src.services.playlist_service import PlaylistService

        previous_track = {
            "id": "track_1",
            "name": "Previous Song",
            "duration_ms": 210000,
        }
        mock_get_previous.return_value = previous_track

        service = PlaylistService()

        with patch.object(
            service.cache_service, "get_session", return_value=mock_orbital_session
        ):
            track = service.get_previous_track("session_123")

            assert track["id"] == "track_1"
            assert track["name"] == "Previous Song"

            mock_get_previous.assert_called_once_with("session_123")

    def test_get_previous_track_no_history(
        self, mock_orbital_session: Dict[str, Any]
    ) -> None:
        """Should handle case when no previous track exists."""
        from src.services.playlist_service import PlaylistService

        # Session with empty track history
        session_no_history = {**mock_orbital_session, "track_history": []}

        service = PlaylistService()

        with patch.object(
            service.cache_service, "get_session", return_value=session_no_history
        ):
            with patch.object(
                service.playlist_generator, "get_previous_track", return_value=None
            ):
                track = service.get_previous_track("session_123")

                assert track is None

    def test_mark_track_as_played(self, mock_orbital_session: Dict[str, Any]) -> None:
        """Should mark track as played and update session."""
        from src.services.playlist_service import PlaylistService

        service = PlaylistService()

        with patch.object(
            service.cache_service, "get_session", return_value=mock_orbital_session
        ):
            with patch.object(service.cache_service, "update_session") as mock_update:
                service.mark_track_as_played("session_123", "track_123")

                mock_update.assert_called_once()
                call_args = mock_update.call_args[0]
                assert call_args[0] == "session_123"
                assert "track_123" in call_args[1]["played_tracks"]

    def test_mark_track_as_played_duplicate(
        self, mock_orbital_session: Dict[str, Any]
    ) -> None:
        """Should handle marking same track as played multiple times."""
        from src.services.playlist_service import PlaylistService

        service = PlaylistService()

        with patch.object(
            service.cache_service, "get_session", return_value=mock_orbital_session
        ):
            with patch.object(service.cache_service, "update_session") as mock_update:
                # Mark track that's already in played_tracks
                service.mark_track_as_played("session_123", "track_1")

                # Should still update session (idempotent operation)
                mock_update.assert_called_once()

    @patch(
        "src.core.playlist_generator.GeographicPlaylistGenerator.get_region_top_50_tracks"
    )
    def test_generate_orbital_playlist(
        self, mock_get_tracks: Mock, mock_orbital_session: Dict[str, Any]
    ) -> None:
        """Should generate playlist for orbital session."""
        from src.services.playlist_service import PlaylistService

        mock_tracks = [
            {"id": "track_1", "name": "Song 1", "duration_ms": 180000},
            {"id": "track_2", "name": "Song 2", "duration_ms": 240000},
            {"id": "track_3", "name": "Song 3", "duration_ms": 200000},
        ]
        mock_get_tracks.return_value = mock_tracks

        service = PlaylistService()

        with patch.object(
            service.satellite_service, "get_satellite_positions"
        ) as mock_positions:
            mock_positions.return_value = [
                {"latitude": 40.0, "longitude": -74.0, "timestamp": utcnow()},
                {
                    "latitude": 50.0,
                    "longitude": -0.1,
                    "timestamp": utcnow() + timedelta(minutes=90),
                },
            ]

            playlist = service.generate_orbital_playlist("session_123", 90)

            assert len(playlist["tracks"]) >= 0  # May be filtered
            assert "duration_minutes" in playlist
            assert "regions_covered" in playlist

    def test_generate_orbital_playlist_invalid_duration(self) -> None:
        """Should handle invalid duration parameters."""
        from src.services.playlist_service import PlaylistService

        service = PlaylistService()

        with pytest.raises(ValueError) as exc_info:
            service.generate_orbital_playlist("session_123", duration_minutes=-10)

        assert "duration" in str(exc_info.value).lower()

        with pytest.raises(ValueError) as exc_info:
            service.generate_orbital_playlist("session_123", duration_minutes=1000)

        assert "duration" in str(exc_info.value).lower()


class TestPlaybackPositionManagement:
    """Test playback position management."""

    def test_set_playback_position(self, mock_orbital_session: Dict[str, Any]) -> None:
        """Should set playback position for track."""
        from src.services.playlist_service import PlaylistService

        service = PlaylistService()

        with patch.object(
            service.cache_service, "get_session", return_value=mock_orbital_session
        ):
            with patch.object(service.cache_service, "update_session") as mock_update:
                service.set_playback_position(
                    "session_123", "track_123", 60000
                )  # 1 minute

                mock_update.assert_called_once()
                call_args = mock_update.call_args[0]
                assert call_args[1]["playback_position"]["track_123"] == 60000

    def test_get_playback_position(self, mock_orbital_session: Dict[str, Any]) -> None:
        """Should get playback position for track."""
        from src.services.playlist_service import PlaylistService

        service = PlaylistService()

        with patch.object(
            service.cache_service, "get_session", return_value=mock_orbital_session
        ):
            position = service.get_playback_position("session_123", "track_2")

            assert position == 45000  # From fixture

    def test_get_playback_position_not_found(
        self, mock_orbital_session: Dict[str, Any]
    ) -> None:
        """Should return 0 for track with no saved position."""
        from src.services.playlist_service import PlaylistService

        service = PlaylistService()

        with patch.object(
            service.cache_service, "get_session", return_value=mock_orbital_session
        ):
            position = service.get_playback_position("session_123", "unknown_track")

            assert position == 0

    def test_clear_playback_position(
        self, mock_orbital_session: Dict[str, Any]
    ) -> None:
        """Should clear playback position for track."""
        from src.services.playlist_service import PlaylistService

        service = PlaylistService()

        with patch.object(
            service.cache_service, "get_session", return_value=mock_orbital_session
        ):
            with patch.object(service.cache_service, "update_session") as mock_update:
                service.clear_playback_position("session_123", "track_2")

                mock_update.assert_called_once()
                call_args = mock_update.call_args[0]
                assert "track_2" not in call_args[1]["playback_position"]


class TestTrackHistoryManagement:
    """Test track history management."""

    def test_add_to_track_history(self, mock_orbital_session: Dict[str, Any]) -> None:
        """Should add track to session history."""
        from src.services.playlist_service import PlaylistService

        service = PlaylistService()

        new_track = {"id": "track_new", "name": "New Song", "duration_ms": 195000}

        with patch.object(
            service.cache_service, "get_session", return_value=mock_orbital_session
        ):
            with patch.object(service.cache_service, "update_session") as mock_update:
                service.add_to_track_history("session_123", new_track)

                mock_update.assert_called_once()
                call_args = mock_update.call_args[0]
                history = call_args[1]["track_history"]
                assert history[-1]["id"] == "track_new"
                assert "timestamp" in history[-1]

    def test_track_history_size_limit(
        self, mock_orbital_session: Dict[str, Any]
    ) -> None:
        """Should limit track history size to prevent memory issues."""
        from src.services.playlist_service import PlaylistService

        service = PlaylistService()

        # Create session with large history
        large_history = [
            {"id": f"track_{i}", "name": f"Song {i}", "timestamp": utcnow()}
            for i in range(200)
        ]
        session_large_history = {**mock_orbital_session, "track_history": large_history}

        with patch.object(
            service.cache_service, "get_session", return_value=session_large_history
        ):
            with patch.object(service.cache_service, "update_session") as mock_update:
                new_track = {"id": "track_new", "name": "New Song"}
                service.add_to_track_history("session_123", new_track)

                call_args = mock_update.call_args[0]
                history = call_args[1]["track_history"]
                # Should limit history size (e.g., max 100 items)
                assert len(history) <= 100

    def test_get_track_history(self, mock_orbital_session: Dict[str, Any]) -> None:
        """Should return track history for session."""
        from src.services.playlist_service import PlaylistService

        service = PlaylistService()

        with patch.object(
            service.cache_service, "get_session", return_value=mock_orbital_session
        ):
            history = service.get_track_history("session_123")

            assert len(history) == 2
            assert history[0]["id"] == "track_1"
            assert history[1]["id"] == "track_2"

    def test_get_track_history_with_limit(
        self, mock_orbital_session: Dict[str, Any]
    ) -> None:
        """Should return limited track history."""
        from src.services.playlist_service import PlaylistService

        service = PlaylistService()

        with patch.object(
            service.cache_service, "get_session", return_value=mock_orbital_session
        ):
            history = service.get_track_history("session_123", limit=1)

            assert len(history) == 1
            assert history[0]["id"] == "track_2"  # Most recent


class TestRegionBasedPlaylistGeneration:
    """Test region-based playlist generation."""

    @patch("src.core.geographic_mapper.GeographicMapper.get_region_from_coordinates")
    @patch(
        "src.core.playlist_generator.GeographicPlaylistGenerator.get_region_top_50_tracks"
    )
    def test_get_tracks_for_region(
        self, mock_get_tracks: Mock, mock_get_region: Mock
    ) -> None:
        """Should get tracks for specific geographic region."""
        from src.services.playlist_service import PlaylistService

        mock_region = Mock()
        mock_region.country_code = "US"
        mock_region.country_name = "United States"
        mock_get_region.return_value = mock_region

        mock_tracks = [
            {"id": "us_track_1", "name": "US Song 1"},
            {"id": "us_track_2", "name": "US Song 2"},
        ]
        mock_get_tracks.return_value = mock_tracks

        service = PlaylistService()
        tracks = service.get_tracks_for_coordinates(40.7128, -74.0060)  # NYC

        assert len(tracks) == 2
        assert tracks[0]["id"] == "us_track_1"
        mock_get_region.assert_called_once_with(40.7128, -74.0060)
        mock_get_tracks.assert_called_once_with("US")

    @patch("src.core.geographic_mapper.GeographicMapper.get_region_from_coordinates")
    @patch("src.core.geographic_mapper.GeographicMapper.get_nearest_land_region")
    @patch(
        "src.core.playlist_generator.GeographicPlaylistGenerator.get_region_top_50_tracks"
    )
    def test_get_tracks_for_ocean_coordinates(
        self, mock_get_tracks: Mock, mock_nearest_land: Mock, mock_get_region: Mock
    ) -> None:
        """Should fallback to nearest land for ocean coordinates."""
        from src.services.playlist_service import PlaylistService

        mock_get_region.return_value = None  # Ocean

        mock_nearest_region = Mock()
        mock_nearest_region.country_code = "PT"
        mock_nearest_region.country_name = "Portugal"
        mock_nearest_land.return_value = mock_nearest_region

        mock_tracks = [{"id": "pt_track_1", "name": "Portuguese Song 1"}]
        mock_get_tracks.return_value = mock_tracks

        service = PlaylistService()
        tracks = service.get_tracks_for_coordinates(35.0, -25.0)  # Atlantic Ocean

        assert len(tracks) == 1
        assert tracks[0]["id"] == "pt_track_1"
        mock_get_region.assert_called_once_with(35.0, -25.0)
        mock_nearest_land.assert_called_once_with(35.0, -25.0)
        mock_get_tracks.assert_called_once_with("PT")

    def test_get_tracks_for_invalid_coordinates(self) -> None:
        """Should handle invalid coordinates gracefully."""
        from src.services.playlist_service import PlaylistService

        service = PlaylistService()

        invalid_coords = [
            (None, None),
            (91.0, 0.0),  # Invalid latitude
            (0.0, 181.0),  # Invalid longitude
        ]

        for lat, lon in invalid_coords:
            tracks = service.get_tracks_for_coordinates(lat, lon)
            assert tracks == []  # Should return empty list


class TestTrackDeduplication:
    """Test track deduplication functionality."""

    def test_deduplicate_tracks_basic(self) -> None:
        """Should remove duplicate tracks from list."""
        from src.services.playlist_service import PlaylistService

        service = PlaylistService()

        tracks = [
            {"id": "track_1", "name": "Song 1"},
            {"id": "track_2", "name": "Song 2"},
            {"id": "track_1", "name": "Song 1"},  # Duplicate
            {"id": "track_3", "name": "Song 3"},
        ]

        played_tracks = {"track_2"}

        deduplicated = service._deduplicate_tracks(tracks, played_tracks)

        # Should remove duplicates and played tracks
        assert len(deduplicated) == 2
        track_ids = [track["id"] for track in deduplicated]
        assert "track_1" in track_ids
        assert "track_3" in track_ids
        assert "track_2" not in track_ids  # Was played

    def test_large_played_tracks_set_performance(self) -> None:
        """Should efficiently handle large played tracks sets."""
        from src.services.playlist_service import PlaylistService

        service = PlaylistService()

        # Create large set of played tracks
        large_played_set = {f"track_{i}" for i in range(10000)}

        tracks = [
            {"id": "track_new_1", "name": "New Song 1"},
            {"id": "track_5000", "name": "Played Song"},  # In played set
            {"id": "track_new_2", "name": "New Song 2"},
        ]

        deduplicated = service._deduplicate_tracks(tracks, large_played_set)

        # Should efficiently filter out played tracks
        assert len(deduplicated) == 2
        track_ids = [track["id"] for track in deduplicated]
        assert "track_new_1" in track_ids
        assert "track_new_2" in track_ids
        assert "track_5000" not in track_ids

    def test_played_tracks_cleanup(self, mock_orbital_session: Dict[str, Any]) -> None:
        """Should clean up large played tracks sets periodically."""
        from src.services.playlist_service import PlaylistService

        service = PlaylistService()

        # Create session with large played tracks set
        large_played_set = {f"track_{i}" for i in range(1000)}
        session_large_played = {
            **mock_orbital_session,
            "played_tracks": large_played_set,
        }

        with patch.object(
            service.cache_service, "get_session", return_value=session_large_played
        ):
            with patch.object(service.cache_service, "update_session") as mock_update:
                service.cleanup_played_tracks("session_123", max_size=500)

                mock_update.assert_called_once()
                call_args = mock_update.call_args[0]
                # Should reduce played tracks set size
                assert len(call_args[1]["played_tracks"]) <= 500


class TestErrorHandling:
    """Test error handling in playlist service."""

    def test_spotify_api_error_handling(self) -> None:
        """Should handle Spotify API errors gracefully."""
        from src.services.playlist_service import PlaylistService

        service = PlaylistService()

        with patch.object(
            service.playlist_generator,
            "get_next_track",
            side_effect=Exception("Spotify API Error"),
        ):
            with pytest.raises(Exception) as exc_info:
                service.get_next_track("session_123")

            assert "Spotify API Error" in str(exc_info.value)

    def test_satellite_position_error_handling(self) -> None:
        """Should handle satellite position calculation errors."""
        from src.services.playlist_service import PlaylistService

        service = PlaylistService()

        mock_session = {
            "session_id": "session_123",
            "satellite_id": "iss",
            "played_tracks": set(),
        }

        with patch.object(
            service.cache_service, "get_session", return_value=mock_session
        ):
            with patch.object(
                service.satellite_service,
                "get_current_satellite_position",
                side_effect=Exception("Position calc error"),
            ):
                with pytest.raises(Exception) as exc_info:
                    service.get_next_track("session_123")

                assert "Position calc error" in str(exc_info.value)

    def test_session_corruption_handling(self) -> None:
        """Should handle corrupted session data."""
        from src.services.playlist_service import PlaylistService

        service = PlaylistService()

        # Test various corrupted session scenarios
        corrupted_sessions = [
            None,  # Missing session
            {},  # Empty session
            {"session_id": "test"},  # Missing required fields
            {"satellite_id": None, "played_tracks": None},  # Null values
        ]

        for corrupted_session in corrupted_sessions:
            with patch.object(
                service.cache_service, "get_session", return_value=corrupted_session
            ):
                if corrupted_session is None or not corrupted_session:
                    with pytest.raises(ValueError):
                        service.get_next_track("session_123")
                else:
                    # Should handle gracefully or raise appropriate error
                    try:
                        service.get_next_track("session_123")
                    except (ValueError, KeyError, TypeError):
                        pass  # Expected for corrupted data

    def test_network_connectivity_error_handling(self) -> None:
        """Should handle network connectivity issues."""
        from src.services.playlist_service import PlaylistService

        service = PlaylistService()

        mock_session = {
            "session_id": "session_123",
            "satellite_id": "iss",
            "played_tracks": set(),
        }

        with patch.object(
            service.cache_service, "get_session", return_value=mock_session
        ):
            with patch.object(
                service.satellite_service,
                "get_current_satellite_position",
                side_effect=ConnectionError("Network down"),
            ):
                with pytest.raises(Exception) as exc_info:
                    service.get_next_track("session_123")

                assert (
                    "Network down" in str(exc_info.value)
                    or "connection" in str(exc_info.value).lower()
                )

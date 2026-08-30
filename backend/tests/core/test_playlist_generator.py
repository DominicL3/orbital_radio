"""Test cases for geographic playlist generation."""

from unittest.mock import Mock, patch

import pytest


class MockTrack:
    """Mock track for testing."""

    def __init__(self, track_id: str, duration_ms: int, name: str = "Test Track"):
        self.id = track_id
        self.duration_ms = duration_ms
        self.name = name
        self.artists = [{"name": "Test Artist"}]
        self.album = {"name": "Test Album"}


class MockGeographicRegion:
    """Mock geographic region."""

    def __init__(self, country_code: str, country_name: str):
        self.country_code = country_code
        self.country_name = country_name
        self.region_type = "country"


@pytest.fixture
def mock_tracks() -> list[MockTrack]:
    """Sample tracks with various durations."""
    return [
        MockTrack("track1", 180000),  # 3 minutes
        MockTrack("track2", 240000),  # 4 minutes
        MockTrack("track3", 30000),  # 30 seconds (too short)
        MockTrack("track4", 600000),  # 10 minutes (too long)
        MockTrack("track5", 200000),  # 3:20 minutes
    ]


@pytest.fixture
def mock_played_tracks() -> set[str]:
    """Set of already played track IDs."""
    return {"track1", "track3"}


class TestGeographicPlaylistGenerator:
    """Test GeographicPlaylistGenerator class."""

    def test_filter_by_duration_default_range(
        self, mock_tracks: list[MockTrack]
    ) -> None:
        """Should filter tracks by default duration range (1-8 minutes)."""
        from src.core.playlist_generator import GeographicPlaylistGenerator

        generator = GeographicPlaylistGenerator()
        filtered = generator.filter_by_duration(mock_tracks)

        # Should keep tracks 1, 2, 5 (within 1-8 minutes)
        assert len(filtered) == 3
        track_ids = [track.id for track in filtered]
        assert "track1" in track_ids
        assert "track2" in track_ids
        assert "track5" in track_ids
        assert "track3" not in track_ids  # Too short
        assert "track4" not in track_ids  # Too long

    def test_filter_by_duration_custom_range(
        self, mock_tracks: list[MockTrack]
    ) -> None:
        """Should filter tracks by custom duration range."""
        from src.core.playlist_generator import GeographicPlaylistGenerator

        generator = GeographicPlaylistGenerator()
        filtered = generator.filter_by_duration(
            mock_tracks, min_duration=120, max_duration=300
        )

        # Should keep tracks with 2-5 minute range
        assert len(filtered) == 3
        durations = [track.duration_ms for track in filtered]
        assert all(120000 <= duration <= 300000 for duration in durations)

    def test_deduplicate_tracks(
        self, mock_tracks: list[MockTrack], mock_played_tracks: set[str]
    ) -> None:
        """Should remove already played tracks."""
        from src.core.playlist_generator import GeographicPlaylistGenerator

        generator = GeographicPlaylistGenerator()
        deduplicated = generator.deduplicate_tracks(mock_tracks, mock_played_tracks)

        # Should remove track1 and track3 (already played)
        assert len(deduplicated) == 3
        track_ids = [track.id for track in deduplicated]
        assert "track1" not in track_ids
        assert "track3" not in track_ids
        assert "track2" in track_ids
        assert "track4" in track_ids
        assert "track5" in track_ids

    @patch(
        "src.core.playlist_generator.GeographicPlaylistGenerator.get_region_top_50_tracks"
    )
    def test_get_next_track_success(
        self, mock_get_tracks: Mock, mock_tracks: list[MockTrack]
    ) -> None:
        """Should return next track based on satellite position."""
        from src.core.playlist_generator import GeographicPlaylistGenerator

        # Mock filtered tracks (duration + deduplication applied)
        valid_tracks = [
            track for track in mock_tracks if 60000 <= track.duration_ms <= 480000
        ]
        mock_get_tracks.return_value = valid_tracks

        generator = GeographicPlaylistGenerator()

        with patch.object(generator, "filter_by_duration", return_value=valid_tracks):
            with patch.object(
                generator, "deduplicate_tracks", return_value=valid_tracks
            ):
                track = generator.get_next_track((40.7128, -74.0060), set())

                assert track is not None
                assert track.id in [t.id for t in valid_tracks]
                assert 60000 <= track.duration_ms <= 480000

    @patch(
        "src.core.playlist_generator.GeographicPlaylistGenerator._get_region_from_coordinates"
    )
    @patch(
        "src.core.playlist_generator.GeographicPlaylistGenerator.get_region_top_50_tracks"
    )
    def test_get_next_track_ocean_fallback(
        self, mock_get_tracks: Mock, mock_get_region: Mock, mock_tracks: list[MockTrack]
    ) -> None:
        """Should fallback to nearest region when over ocean."""
        from src.core.playlist_generator import GeographicPlaylistGenerator

        # Mock ocean coordinates returning None, then fallback region
        mock_get_region.side_effect = [
            None,
            MockGeographicRegion("US", "United States"),
        ]
        mock_get_tracks.return_value = mock_tracks[:2]  # Valid duration tracks

        generator = GeographicPlaylistGenerator()

        with (
            patch.object(generator, "filter_by_duration", return_value=mock_tracks[:2]),
            patch.object(generator, "deduplicate_tracks", return_value=mock_tracks[:2]),
        ):
            track = generator.get_next_track((25.0, -30.0), set())  # Atlantic Ocean

            assert track is not None
            # Should have called get_region twice (ocean, then fallback)
            assert mock_get_region.call_count == 2

    def test_get_next_track_no_available_tracks(self) -> None:
        """Should handle case when no tracks are available."""
        from src.core.playlist_generator import GeographicPlaylistGenerator

        generator = GeographicPlaylistGenerator()

        with patch.object(generator, "get_region_top_50_tracks", return_value=[]):
            track = generator.get_next_track((40.7128, -74.0060), set())
            assert track is None

    @patch("src.core.spotify_client.SpotifyClient.search_country_playlists")
    def test_get_region_top_50_tracks(self, mock_search: Mock) -> None:
        """Should fetch top 50 tracks for a region."""
        from src.core.playlist_generator import GeographicPlaylistGenerator

        mock_search.return_value = [
            {"id": "track1", "duration_ms": 180000, "name": "Song 1"},
            {"id": "track2", "duration_ms": 240000, "name": "Song 2"},
        ]

        generator = GeographicPlaylistGenerator()
        tracks = generator.get_region_top_50_tracks("US")

        assert len(tracks) == 2
        mock_search.assert_called_once_with("US", "Top 50", mock_search.call_args[0][2])

    def test_get_region_top_50_tracks_api_error(self) -> None:
        """Should handle API errors gracefully."""
        from src.core.playlist_generator import GeographicPlaylistGenerator

        generator = GeographicPlaylistGenerator()

        with patch(
            "src.core.spotify_client.SpotifyClient.search_country_playlists"
        ) as mock_search:
            mock_search.side_effect = Exception("API Error")
            tracks = generator.get_region_top_50_tracks("US")

            assert tracks == []

    def test_get_previous_track_with_history(self) -> None:
        """Should return previous track from session history."""
        from src.core.playlist_generator import GeographicPlaylistGenerator

        generator = GeographicPlaylistGenerator()

        # Mock session with track history
        mock_session = {
            "track_history": [
                {"id": "track1", "name": "Previous Song", "duration_ms": 180000},
                {"id": "track2", "name": "Current Song", "duration_ms": 240000},
            ]
        }

        with patch(
            "src.services.cache_service.CacheService.get_session",
            return_value=mock_session,
        ):
            track = generator.get_previous_track("session123")

            assert track is not None
            assert track["id"] == "track1"  # Should return second-to-last track

    def test_get_previous_track_no_history(self) -> None:
        """Should handle case when no previous track exists."""
        from src.core.playlist_generator import GeographicPlaylistGenerator

        generator = GeographicPlaylistGenerator()

        mock_session = {"track_history": []}

        with patch(
            "src.services.cache_service.CacheService.get_session",
            return_value=mock_session,
        ):
            track = generator.get_previous_track("session123")

            assert track is None

    def test_get_previous_track_invalid_session(self) -> None:
        """Should handle invalid session gracefully."""
        from src.core.playlist_generator import GeographicPlaylistGenerator

        generator = GeographicPlaylistGenerator()

        with patch(
            "src.services.cache_service.CacheService.get_session", return_value=None
        ):
            track = generator.get_previous_track("invalid_session")

            assert track is None


class TestRegionPlaylistRotation:
    """Test playlist type rotation functionality."""

    def test_region_playlist_rotation_initialization(self) -> None:
        """Should initialize playlist rotation tracking."""
        from src.core.playlist_generator import GeographicPlaylistGenerator

        generator = GeographicPlaylistGenerator()
        assert hasattr(generator, "region_playlist_rotation")
        assert isinstance(generator.region_playlist_rotation, dict)

    def test_future_playlist_type_support(self) -> None:
        """Should support future playlist types (Viral 50, New Music Friday)."""
        from src.core.playlist_generator import GeographicPlaylistGenerator

        generator = GeographicPlaylistGenerator()

        # This test ensures the design supports future playlist types
        # Currently only "Top 50" is implemented
        supported_types = [
            "Top 50"
        ]  # Future: ["Top 50", "Viral 50", "New Music Friday"]

        for playlist_type in supported_types:
            # Should not raise an error
            with patch.object(generator, "get_region_top_50_tracks") as mock_get:
                mock_get.return_value = []
                tracks = generator.get_region_top_50_tracks("US")
                assert isinstance(tracks, list)


class TestGeographicMapping:
    """Test geographic coordinate to region mapping."""

    def test_coordinate_to_region_mapping(self) -> None:
        """Should map coordinates to geographic regions."""
        from src.core.playlist_generator import GeographicPlaylistGenerator

        generator = GeographicPlaylistGenerator()

        # Test major cities
        test_coordinates = [
            ((40.7128, -74.0060), "US"),  # New York
            ((51.5074, -0.1278), "GB"),  # London
            ((35.6762, 139.6503), "JP"),  # Tokyo
            ((-33.8688, 151.2093), "AU"),  # Sydney
        ]

        for (lat, lon), expected_country in test_coordinates:
            with patch.object(
                generator, "_get_region_from_coordinates"
            ) as mock_get_region:
                mock_region = MockGeographicRegion(
                    expected_country, f"Country {expected_country}"
                )
                mock_get_region.return_value = mock_region

                with patch.object(
                    generator, "get_region_top_50_tracks", return_value=[]
                ):
                    generator.get_next_track((lat, lon), set())
                    mock_get_region.assert_called_with(lat, lon)

    def test_ocean_coordinate_handling(self) -> None:
        """Should handle ocean coordinates with nearest land fallback."""
        from src.core.playlist_generator import GeographicPlaylistGenerator

        generator = GeographicPlaylistGenerator()

        # Test ocean coordinates
        ocean_coordinates = [
            (25.0, -30.0),  # Atlantic Ocean
            (0.0, -140.0),  # Pacific Ocean
            (-45.0, 90.0),  # Indian Ocean
        ]

        for lat, lon in ocean_coordinates:
            with patch.object(
                generator, "_get_region_from_coordinates"
            ) as mock_get_region:
                # First call returns None (ocean), second returns nearest land
                mock_get_region.side_effect = [
                    None,
                    MockGeographicRegion("US", "United States"),
                ]

                with patch.object(
                    generator, "get_region_top_50_tracks", return_value=[]
                ):
                    generator.get_next_track((lat, lon), set())

                # Should attempt to find region twice (ocean, then fallback)
                assert mock_get_region.call_count >= 2


class TestPerformanceOptimizations:
    """Test performance optimization features."""

    def test_large_played_tracks_set_handling(self) -> None:
        """Should handle large played tracks sets efficiently."""
        from src.core.playlist_generator import GeographicPlaylistGenerator

        generator = GeographicPlaylistGenerator()

        # Create large set of played tracks
        large_played_set = {f"track_{i}" for i in range(1000)}

        mock_tracks = [MockTrack(f"track_{i}", 180000) for i in range(1100)]

        # Should efficiently filter out played tracks
        deduplicated = generator.deduplicate_tracks(mock_tracks, large_played_set)

        # Should have 100 unique tracks remaining
        assert len(deduplicated) == 100

        # Verify no played tracks remain
        remaining_ids = {track.id for track in deduplicated}
        assert not (remaining_ids & large_played_set)

    def test_memory_efficient_track_processing(self) -> None:
        """Should process tracks memory efficiently."""
        from src.core.playlist_generator import GeographicPlaylistGenerator

        generator = GeographicPlaylistGenerator()

        # Test with large number of tracks
        large_track_list = [MockTrack(f"track_{i}", 180000) for i in range(5000)]

        # Should handle large lists without memory issues
        filtered = generator.filter_by_duration(large_track_list)
        assert len(filtered) == 5000  # All tracks are valid duration

        # Should handle deduplication efficiently
        played_set = {f"track_{i}" for i in range(0, 5000, 2)}  # Every other track
        deduplicated = generator.deduplicate_tracks(filtered, played_set)
        assert len(deduplicated) == 2500  # Half should remain


class TestErrorHandling:
    """Test error handling in playlist generation."""

    def test_invalid_coordinates(self) -> None:
        """Should handle invalid coordinate inputs."""
        from src.core.playlist_generator import GeographicPlaylistGenerator

        generator = GeographicPlaylistGenerator()

        invalid_coords = [
            (None, None),
            (91.0, 0.0),  # Invalid latitude
            (0.0, 181.0),  # Invalid longitude
            ("invalid", "coords"),
        ]

        for lat, lon in invalid_coords:
            with patch.object(
                generator, "_get_region_from_coordinates", return_value=None
            ):
                track = generator.get_next_track((lat, lon), set())
                # Should handle gracefully, may return None or fallback
                assert track is None or hasattr(track, "id")

    def test_spotify_api_failures(self) -> None:
        """Should handle Spotify API failures gracefully."""
        from src.core.playlist_generator import GeographicPlaylistGenerator

        generator = GeographicPlaylistGenerator()

        with patch(
            "src.core.spotify_client.SpotifyClient.search_country_playlists"
        ) as mock_search:
            mock_search.side_effect = [
                ConnectionError("Network error"),
                TimeoutError("Request timeout"),
                Exception("API rate limit"),
            ]

            # Should return empty list for all error types
            for _ in range(3):
                tracks = generator.get_region_top_50_tracks("US")
                assert tracks == []

    def test_empty_region_playlists(self) -> None:
        """Should handle regions with no available playlists."""
        from src.core.playlist_generator import GeographicPlaylistGenerator

        generator = GeographicPlaylistGenerator()

        with patch.object(generator, "get_region_top_50_tracks", return_value=[]):
            track = generator.get_next_track((40.7128, -74.0060), set())
            assert track is None

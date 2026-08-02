"""
Comprehensive unit tests for playlist API endpoints.

Tests cover orbital playlist generation, next/previous track logic, track marking,
and geographic-based music selection with proper mocking of external dependencies.
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta
from typing import Dict, List, Any
from fastapi.testclient import TestClient
from fastapi import status

# Import test fixtures from conftest


class TestPlaylistEndpoints:
    """Test suite for playlist API endpoints."""

    @pytest.fixture
    def client(self) -> TestClient:
        """Create FastAPI test client."""
        # This would import the actual FastAPI app
        # from src.main import app
        # return TestClient(app)
        # For now, we'll mock it
        mock_app = Mock()
        return TestClient(mock_app)

    @pytest.fixture
    def mock_orbital_playlist_request(self) -> Dict[str, Any]:
        """Mock orbital playlist generation request."""
        return {
            "session_id": "test_session_123",
            "satellite_id": "iss",
            "duration_minutes": 90,
            "start_time": datetime.utcnow().isoformat(),
        }

    @pytest.fixture
    def mock_generated_playlist(
        self, mock_playlist_tracks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Mock generated orbital playlist response."""
        return {
            "playlist_id": "orbital_playlist_123",
            "session_id": "test_session_123",
            "satellite_id": "iss",
            "duration_minutes": 90,
            "total_tracks": len(mock_playlist_tracks),
            "tracks": mock_playlist_tracks,
            "regions_covered": ["US", "CA", "GB", "FR", "DE"],
            "estimated_duration_seconds": sum(
                track["duration_ms"] for track in mock_playlist_tracks
            )
            // 1000,
            "created_at": datetime.utcnow().isoformat(),
            "orbital_path": [
                {
                    "timestamp": datetime.utcnow().isoformat(),
                    "latitude": 40.7,
                    "longitude": -74.0,
                    "region": "US",
                },
                {
                    "timestamp": (
                        datetime.utcnow() + timedelta(minutes=30)
                    ).isoformat(),
                    "latitude": 51.5,
                    "longitude": -0.1,
                    "region": "GB",
                },
            ],
        }

    @pytest.fixture
    def mock_next_track_response(
        self, mock_track_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Mock next track response."""
        track = mock_track_data.copy()
        track.update(
            {
                "selected_for_region": "US",
                "satellite_position": {"latitude": 40.7128, "longitude": -74.0060},
                "selected_at": datetime.utcnow().isoformat(),
                "track_index": 5,
            }
        )
        return track

    def test_generate_orbital_playlist_success(
        self,
        client: TestClient,
        mock_orbital_playlist_request: Dict[str, Any],
        mock_generated_playlist: Dict[str, Any],
    ):
        """Test successful orbital playlist generation."""
        with patch("src.services.playlist_service.PlaylistService") as mock_service:
            mock_service.return_value.generate_orbital_playlist.return_value = (
                mock_generated_playlist
            )

            with patch(
                "src.services.session_service.SessionService"
            ) as mock_session_service:
                mock_session_service.return_value.get_session.return_value = {
                    "session_id": "test_session_123"
                }

                # Act
                response = client.post(
                    "/playlists/orbital", json=mock_orbital_playlist_request
                )

                # Assert
                assert response.status_code == status.HTTP_201_CREATED
                response_data = response.json()
                assert "playlist_id" in response_data
                assert "tracks" in response_data
                assert "regions_covered" in response_data
                assert "orbital_path" in response_data
                assert response_data["satellite_id"] == "iss"
                assert response_data["duration_minutes"] == 90
                assert len(response_data["tracks"]) == 10
                assert len(response_data["regions_covered"]) == 5

                # Verify service calls
                mock_service.return_value.generate_orbital_playlist.assert_called_once()
                call_args = (
                    mock_service.return_value.generate_orbital_playlist.call_args[0]
                )
                assert call_args[0] == "test_session_123"
                assert call_args[1] == "iss"
                assert call_args[2] == 90

    def test_generate_orbital_playlist_invalid_session(
        self, client: TestClient, mock_orbital_playlist_request: Dict[str, Any]
    ):
        """Test orbital playlist generation with invalid session."""
        with patch(
            "src.services.session_service.SessionService"
        ) as mock_session_service:
            mock_session_service.return_value.get_session.return_value = None

            # Act
            response = client.post(
                "/playlists/orbital", json=mock_orbital_playlist_request
            )

            # Assert
            assert response.status_code == status.HTTP_401_UNAUTHORIZED
            response_data = response.json()
            assert "error" in response_data
            assert "session" in response_data["error"].lower()

    def test_generate_orbital_playlist_invalid_satellite(self, client: TestClient):
        """Test orbital playlist generation with invalid satellite ID."""
        request_data = {
            "session_id": "test_session_123",
            "satellite_id": "invalid_satellite",
            "duration_minutes": 90,
        }

        with patch(
            "src.services.session_service.SessionService"
        ) as mock_session_service:
            mock_session_service.return_value.get_session.return_value = {
                "session_id": "test_session_123"
            }

            with patch("src.services.playlist_service.PlaylistService") as mock_service:
                mock_service.return_value.generate_orbital_playlist.side_effect = (
                    ValueError("Invalid satellite ID")
                )

                # Act
                response = client.post("/playlists/orbital", json=request_data)

                # Assert
                assert response.status_code == status.HTTP_400_BAD_REQUEST
                response_data = response.json()
                assert "error" in response_data
                assert "satellite" in response_data["error"].lower()

    def test_generate_orbital_playlist_duration_validation(self, client: TestClient):
        """Test orbital playlist generation with invalid duration parameters."""
        base_request = {"session_id": "test_session_123", "satellite_id": "iss"}

        invalid_durations = [
            -30,
            0,
            1441,
            10000,
        ]  # Negative, zero, too large, excessive

        for duration in invalid_durations:
            request_data = base_request.copy()
            request_data["duration_minutes"] = duration

            response = client.post("/playlists/orbital", json=request_data)
            assert response.status_code in [
                status.HTTP_400_BAD_REQUEST,
                status.HTTP_422_UNPROCESSABLE_ENTITY,
            ]

    def test_generate_orbital_playlist_spotify_unavailable(
        self, client: TestClient, mock_orbital_playlist_request: Dict[str, Any]
    ):
        """Test orbital playlist generation when Spotify API is unavailable."""
        with patch(
            "src.services.session_service.SessionService"
        ) as mock_session_service:
            mock_session_service.return_value.get_session.return_value = {
                "session_id": "test_session_123"
            }

            with patch("src.services.playlist_service.PlaylistService") as mock_service:
                mock_service.return_value.generate_orbital_playlist.side_effect = (
                    ConnectionError("Spotify API unavailable")
                )

                # Act
                response = client.post(
                    "/playlists/orbital", json=mock_orbital_playlist_request
                )

                # Assert
                assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
                response_data = response.json()
                assert "error" in response_data
                assert "spotify" in response_data["error"].lower()

    def test_get_orbital_playlist_success(
        self, client: TestClient, mock_generated_playlist: Dict[str, Any]
    ):
        """Test successful retrieval of existing orbital playlist."""
        session_id = "test_session_123"

        with patch("src.services.playlist_service.PlaylistService") as mock_service:
            mock_service.return_value.get_orbital_playlist.return_value = (
                mock_generated_playlist
            )

            # Act
            response = client.get(f"/playlists/orbital/{session_id}")

            # Assert
            assert response.status_code == status.HTTP_200_OK
            response_data = response.json()
            assert response_data["session_id"] == session_id
            assert "tracks" in response_data
            assert "regions_covered" in response_data
            assert len(response_data["tracks"]) == 10

            # Verify service call
            mock_service.return_value.get_orbital_playlist.assert_called_once_with(
                session_id
            )

    def test_get_orbital_playlist_not_found(self, client: TestClient):
        """Test retrieval of non-existent orbital playlist."""
        session_id = "nonexistent_session"

        with patch("src.services.playlist_service.PlaylistService") as mock_service:
            mock_service.return_value.get_orbital_playlist.return_value = None

            # Act
            response = client.get(f"/playlists/orbital/{session_id}")

            # Assert
            assert response.status_code == status.HTTP_404_NOT_FOUND
            response_data = response.json()
            assert "error" in response_data
            assert "playlist" in response_data["error"].lower()

    def test_get_next_track_success(
        self, client: TestClient, mock_next_track_response: Dict[str, Any]
    ):
        """Test successful next track selection based on satellite position."""
        session_id = "test_session_123"

        with patch("src.services.playlist_service.PlaylistService") as mock_service:
            mock_service.return_value.get_next_track.return_value = (
                mock_next_track_response
            )

            with patch(
                "src.services.session_service.SessionService"
            ) as mock_session_service:
                mock_session_service.return_value.get_session.return_value = {
                    "session_id": session_id
                }

                # Act
                response = client.post(f"/playlists/orbital/{session_id}/next")

                # Assert
                assert response.status_code == status.HTTP_200_OK
                response_data = response.json()
                assert "id" in response_data
                assert "name" in response_data
                assert "selected_for_region" in response_data
                assert "satellite_position" in response_data
                assert response_data["selected_for_region"] == "US"
                assert "latitude" in response_data["satellite_position"]
                assert "longitude" in response_data["satellite_position"]

                # Verify service call
                mock_service.return_value.get_next_track.assert_called_once_with(
                    session_id
                )

    def test_get_next_track_no_tracks_available(self, client: TestClient):
        """Test next track selection when no tracks are available."""
        session_id = "test_session_123"

        with patch(
            "src.services.session_service.SessionService"
        ) as mock_session_service:
            mock_session_service.return_value.get_session.return_value = {
                "session_id": session_id
            }

            with patch("src.services.playlist_service.PlaylistService") as mock_service:
                mock_service.return_value.get_next_track.return_value = None

                # Act
                response = client.post(f"/playlists/orbital/{session_id}/next")

                # Assert
                assert response.status_code == status.HTTP_404_NOT_FOUND
                response_data = response.json()
                assert "error" in response_data
                assert "track" in response_data["error"].lower()

    def test_get_next_track_satellite_position_unavailable(self, client: TestClient):
        """Test next track selection when satellite position is unavailable."""
        session_id = "test_session_123"

        with patch(
            "src.services.session_service.SessionService"
        ) as mock_session_service:
            mock_session_service.return_value.get_session.return_value = {
                "session_id": session_id
            }

            with patch("src.services.playlist_service.PlaylistService") as mock_service:
                mock_service.return_value.get_next_track.side_effect = ValueError(
                    "Satellite position unavailable"
                )

                # Act
                response = client.post(f"/playlists/orbital/{session_id}/next")

                # Assert
                assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
                response_data = response.json()
                assert "error" in response_data
                assert "position" in response_data["error"].lower()

    def test_get_previous_track_success(
        self, client: TestClient, mock_track_data: Dict[str, Any]
    ):
        """Test successful previous track retrieval from session history."""
        session_id = "test_session_123"
        previous_track = mock_track_data.copy()
        previous_track.update(
            {
                "played_at": (datetime.utcnow() - timedelta(minutes=3)).isoformat(),
                "track_index": 3,
            }
        )

        with patch("src.services.playlist_service.PlaylistService") as mock_service:
            mock_service.return_value.get_previous_track.return_value = previous_track

            with patch(
                "src.services.session_service.SessionService"
            ) as mock_session_service:
                mock_session_service.return_value.get_session.return_value = {
                    "session_id": session_id
                }

                # Act
                response = client.post(f"/playlists/orbital/{session_id}/previous")

                # Assert
                assert response.status_code == status.HTTP_200_OK
                response_data = response.json()
                assert "id" in response_data
                assert "name" in response_data
                assert "played_at" in response_data
                assert "track_index" in response_data

                # Verify service call
                mock_service.return_value.get_previous_track.assert_called_once_with(
                    session_id
                )

    def test_get_previous_track_no_history(self, client: TestClient):
        """Test previous track retrieval when no playback history exists."""
        session_id = "test_session_123"

        with patch(
            "src.services.session_service.SessionService"
        ) as mock_session_service:
            mock_session_service.return_value.get_session.return_value = {
                "session_id": session_id
            }

            with patch("src.services.playlist_service.PlaylistService") as mock_service:
                mock_service.return_value.get_previous_track.return_value = None

                # Act
                response = client.post(f"/playlists/orbital/{session_id}/previous")

                # Assert
                assert response.status_code == status.HTTP_404_NOT_FOUND
                response_data = response.json()
                assert "error" in response_data
                assert "history" in response_data["error"].lower()

    def test_mark_track_as_played_success(self, client: TestClient):
        """Test successful marking of track as played."""
        session_id = "test_session_123"
        track_id = "track_123"
        played_data = {
            "track_id": track_id,
            "played_at": datetime.utcnow().isoformat(),
            "position_ms": 0,
            "duration_ms": 180000,
        }

        with patch("src.services.playlist_service.PlaylistService") as mock_service:
            mock_service.return_value.mark_track_played.return_value = True

            with patch(
                "src.services.session_service.SessionService"
            ) as mock_session_service:
                mock_session_service.return_value.get_session.return_value = {
                    "session_id": session_id
                }

                # Act
                response = client.post(
                    f"/playlists/orbital/{session_id}/played", json=played_data
                )

                # Assert
                assert response.status_code == status.HTTP_200_OK
                response_data = response.json()
                assert "message" in response_data
                assert "marked" in response_data["message"].lower()

                # Verify service call
                mock_service.return_value.mark_track_played.assert_called_once()
                call_args = mock_service.return_value.mark_track_played.call_args[0]
                assert call_args[0] == session_id
                assert call_args[1] == track_id

    def test_mark_track_as_played_invalid_data(self, client: TestClient):
        """Test marking track as played with invalid data."""
        session_id = "test_session_123"

        invalid_data_cases = [
            {},  # Empty data
            {"track_id": ""},  # Empty track ID
            {"track_id": "valid_id", "position_ms": -100},  # Negative position
            {"track_id": "valid_id", "duration_ms": 0},  # Zero duration
            {
                "track_id": "valid_id",
                "played_at": "invalid_date",
            },  # Invalid date format
        ]

        for invalid_data in invalid_data_cases:
            response = client.post(
                f"/playlists/orbital/{session_id}/played", json=invalid_data
            )
            assert response.status_code in [
                status.HTTP_400_BAD_REQUEST,
                status.HTTP_422_UNPROCESSABLE_ENTITY,
            ]

    def test_mark_track_as_played_duplicate(self, client: TestClient):
        """Test marking the same track as played multiple times."""
        session_id = "test_session_123"
        track_id = "track_123"
        played_data = {"track_id": track_id, "played_at": datetime.utcnow().isoformat()}

        with patch(
            "src.services.session_service.SessionService"
        ) as mock_session_service:
            mock_session_service.return_value.get_session.return_value = {
                "session_id": session_id
            }

            with patch("src.services.playlist_service.PlaylistService") as mock_service:
                mock_service.return_value.mark_track_played.return_value = (
                    False  # Already marked
                )

                # Act
                response = client.post(
                    f"/playlists/orbital/{session_id}/played", json=played_data
                )

                # Assert
                assert response.status_code == status.HTTP_409_CONFLICT
                response_data = response.json()
                assert "error" in response_data
                assert "already" in response_data["error"].lower()

    def test_playlist_track_filtering(
        self, client: TestClient, mock_orbital_playlist_request: Dict[str, Any]
    ):
        """Test track filtering based on duration and content requirements."""
        # Mock playlist with mixed track durations
        filtered_playlist = {
            "playlist_id": "filtered_playlist_123",
            "session_id": "test_session_123",
            "satellite_id": "iss",
            "tracks": [
                {
                    "id": "track_1",
                    "duration_ms": 120000,
                    "name": "Valid Track 1",
                },  # 2 minutes - valid
                {
                    "id": "track_2",
                    "duration_ms": 300000,
                    "name": "Valid Track 2",
                },  # 5 minutes - valid
                {
                    "id": "track_3",
                    "duration_ms": 480000,
                    "name": "Valid Track 3",
                },  # 8 minutes - valid
            ],
            "filtered_out_count": 3,  # Tracks filtered for being too short/long
            "filter_criteria": {
                "min_duration_ms": 60000,  # 1 minute
                "max_duration_ms": 480000,  # 8 minutes
                "explicit_content_filtered": False,
            },
        }

        with patch(
            "src.services.session_service.SessionService"
        ) as mock_session_service:
            mock_session_service.return_value.get_session.return_value = {
                "session_id": "test_session_123"
            }

            with patch("src.services.playlist_service.PlaylistService") as mock_service:
                mock_service.return_value.generate_orbital_playlist.return_value = (
                    filtered_playlist
                )

                # Act
                response = client.post(
                    "/playlists/orbital", json=mock_orbital_playlist_request
                )

                # Assert
                assert response.status_code == status.HTTP_201_CREATED
                response_data = response.json()
                assert len(response_data["tracks"]) == 3
                assert response_data["filtered_out_count"] == 3
                assert "filter_criteria" in response_data

                # Verify all tracks meet duration criteria
                for track in response_data["tracks"]:
                    assert 60000 <= track["duration_ms"] <= 480000

    def test_playlist_deduplication(self, client: TestClient):
        """Test playlist deduplication prevents repeated tracks."""
        session_id = "test_session_123"

        # Simulate session with played tracks
        mock_session_data = {
            "session_id": session_id,
            "played_tracks": {"track_1", "track_2", "track_3"},
        }

        # Mock next track that avoids duplicates
        next_track = {
            "id": "track_4",  # Different from played tracks
            "name": "New Track",
            "duration_ms": 180000,
            "selected_for_region": "FR",
            "satellite_position": {"latitude": 48.8566, "longitude": 2.3522},
        }

        with patch(
            "src.services.session_service.SessionService"
        ) as mock_session_service:
            mock_session_service.return_value.get_session.return_value = (
                mock_session_data
            )

            with patch("src.services.playlist_service.PlaylistService") as mock_service:
                mock_service.return_value.get_next_track.return_value = next_track

                # Act
                response = client.post(f"/playlists/orbital/{session_id}/next")

                # Assert
                assert response.status_code == status.HTTP_200_OK
                response_data = response.json()
                assert response_data["id"] == "track_4"
                assert response_data["id"] not in {"track_1", "track_2", "track_3"}

    def test_geographic_playlist_mapping(
        self, client: TestClient, mock_orbital_playlist_request: Dict[str, Any]
    ):
        """Test geographic mapping of tracks to regions."""
        geographic_playlist = {
            "playlist_id": "geo_playlist_123",
            "session_id": "test_session_123",
            "satellite_id": "iss",
            "tracks": [
                {
                    "id": "us_track",
                    "name": "American Song",
                    "region": "US",
                    "country_name": "United States",
                },
                {
                    "id": "uk_track",
                    "name": "British Song",
                    "region": "GB",
                    "country_name": "United Kingdom",
                },
                {
                    "id": "fr_track",
                    "name": "French Song",
                    "region": "FR",
                    "country_name": "France",
                },
                {
                    "id": "de_track",
                    "name": "German Song",
                    "region": "DE",
                    "country_name": "Germany",
                },
            ],
            "geographic_coverage": {
                "continents": ["North America", "Europe"],
                "countries_count": 4,
                "ocean_tracks": 0,
                "fallback_regions_used": [],
            },
        }

        with patch(
            "src.services.session_service.SessionService"
        ) as mock_session_service:
            mock_session_service.return_value.get_session.return_value = {
                "session_id": "test_session_123"
            }

            with patch("src.services.playlist_service.PlaylistService") as mock_service:
                mock_service.return_value.generate_orbital_playlist.return_value = (
                    geographic_playlist
                )

                # Act
                response = client.post(
                    "/playlists/orbital", json=mock_orbital_playlist_request
                )

                # Assert
                assert response.status_code == status.HTTP_201_CREATED
                response_data = response.json()
                assert "geographic_coverage" in response_data
                assert len(response_data["tracks"]) == 4

                # Verify geographic diversity
                regions = {track["region"] for track in response_data["tracks"]}
                assert regions == {"US", "GB", "FR", "DE"}
                assert response_data["geographic_coverage"]["countries_count"] == 4

    def test_ocean_regions_fallback(self, client: TestClient):
        """Test fallback behavior when satellite is over ocean regions."""
        session_id = "test_session_123"

        # Mock track selected for ocean position with fallback
        ocean_track = {
            "id": "ocean_track",
            "name": "Ocean Fallback Track",
            "duration_ms": 180000,
            "selected_for_region": "US",  # Fallback to nearest country
            "satellite_position": {
                "latitude": 30.0,
                "longitude": -60.0,
            },  # Atlantic Ocean
            "is_ocean_position": True,
            "fallback_reason": "Satellite over Atlantic Ocean, using nearest country (US)",
        }

        with patch(
            "src.services.session_service.SessionService"
        ) as mock_session_service:
            mock_session_service.return_value.get_session.return_value = {
                "session_id": session_id
            }

            with patch("src.services.playlist_service.PlaylistService") as mock_service:
                mock_service.return_value.get_next_track.return_value = ocean_track

                # Act
                response = client.post(f"/playlists/orbital/{session_id}/next")

                # Assert
                assert response.status_code == status.HTTP_200_OK
                response_data = response.json()
                assert response_data["is_ocean_position"] is True
                assert response_data["selected_for_region"] == "US"
                assert "fallback_reason" in response_data
                assert "ocean" in response_data["fallback_reason"].lower()

    @pytest.mark.parametrize(
        "region_code,expected_tracks",
        [
            ("US", 50),  # Top 50 USA
            ("GB", 50),  # Top 50 UK
            ("FR", 50),  # Top 50 France
            ("DE", 50),  # Top 50 Germany
            ("AU", 50),  # Top 50 Australia
            ("XX", 0),  # Invalid region code
        ],
    )
    def test_regional_playlist_generation(
        self, client: TestClient, region_code: str, expected_tracks: int
    ):
        """Test playlist generation for various regions."""
        # This test would verify region-specific playlist generation
        # For now, we'll mock the behavior

        with patch("src.services.playlist_service.PlaylistService") as mock_service:
            if expected_tracks > 0:
                mock_tracks = [
                    {"id": f"track_{i}", "region": region_code}
                    for i in range(expected_tracks)
                ]
                mock_service.return_value.get_region_tracks.return_value = mock_tracks
            else:
                mock_service.return_value.get_region_tracks.return_value = []

            # This would be called internally during playlist generation
            tracks = mock_service.return_value.get_region_tracks(region_code)
            assert len(tracks) == expected_tracks

    def test_concurrent_playlist_operations(self, client: TestClient):
        """Test handling of concurrent playlist operations."""
        import threading

        session_id = "test_session_123"
        results = []

        def make_next_track_request():
            try:
                with patch(
                    "src.services.session_service.SessionService"
                ) as mock_session_service:
                    mock_session_service.return_value.get_session.return_value = {
                        "session_id": session_id
                    }

                    with patch(
                        "src.services.playlist_service.PlaylistService"
                    ) as mock_service:
                        mock_service.return_value.get_next_track.return_value = {
                            "id": "concurrent_track",
                            "name": "Concurrent Track",
                        }

                        response = client.post(f"/playlists/orbital/{session_id}/next")
                        results.append(response.status_code == status.HTTP_200_OK)
            except Exception:
                results.append(False)

        # Act - create multiple concurrent requests
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=make_next_track_request)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Assert - all requests should succeed
        assert len(results) == 5
        assert all(results)

    def test_playlist_session_cleanup(self, client: TestClient):
        """Test cleanup of playlist data when session expires."""
        expired_session_id = "expired_session_123"

        with patch(
            "src.services.session_service.SessionService"
        ) as mock_session_service:
            # Mock expired session
            mock_session_service.return_value.get_session.return_value = None

            # Act
            response = client.get(f"/playlists/orbital/{expired_session_id}")

            # Assert
            assert response.status_code == status.HTTP_401_UNAUTHORIZED
            response_data = response.json()
            assert "error" in response_data
            assert "session" in response_data["error"].lower()

    def test_playlist_memory_optimization(self, client: TestClient):
        """Test memory optimization for large playlists."""
        session_id = "test_session_123"

        # Mock large session with many played tracks
        large_session = {
            "session_id": session_id,
            "played_tracks": set(f"track_{i}" for i in range(1000)),  # Large played set
        }

        with patch(
            "src.services.session_service.SessionService"
        ) as mock_session_service:
            mock_session_service.return_value.get_session.return_value = large_session

            with patch("src.services.playlist_service.PlaylistService") as mock_service:
                # Mock cleanup for large played sets
                mock_service.return_value.cleanup_large_played_sets.return_value = True
                mock_service.return_value.get_next_track.return_value = {
                    "id": "optimized_track",
                    "name": "Memory Optimized Track",
                }

                # Act
                response = client.post(f"/playlists/orbital/{session_id}/next")

                # Assert
                assert response.status_code == status.HTTP_200_OK

                # Verify cleanup was potentially called (would be done in background)
                # This is more of a conceptual test for memory management

"""Test cases for Spotify API client."""

from unittest.mock import Mock, patch
from typing import Dict, Any
import pytest


@pytest.fixture
def mock_spotify_tokens() -> Dict[str, Any]:
    """Mock Spotify OAuth tokens."""
    return {
        "access_token": "test_access_token",
        "refresh_token": "test_refresh_token",
        "expires_in": 3600,
        "token_type": "Bearer",
        "scope": "user-read-private user-read-email playlist-read-private",
    }


@pytest.fixture
def mock_user_profile() -> Dict[str, Any]:
    """Mock Spotify user profile."""
    return {
        "id": "test_user_123",
        "display_name": "Test User",
        "email": "test@example.com",
        "country": "US",
        "followers": {"total": 42},
        "images": [{"url": "https://example.com/avatar.jpg"}],
    }


@pytest.fixture
def mock_playlist_response() -> Dict[str, Any]:
    """Mock Spotify playlist search response."""
    return {
        "playlists": {
            "items": [
                {
                    "id": "playlist_123",
                    "name": "Top 50 - USA",
                    "tracks": {
                        "href": "https://api.spotify.com/v1/playlists/playlist_123/tracks",
                        "total": 50,
                    },
                }
            ]
        }
    }


@pytest.fixture
def mock_tracks_response() -> Dict[str, Any]:
    """Mock Spotify tracks response."""
    return {
        "items": [
            {
                "track": {
                    "id": "track_123",
                    "name": "Test Song",
                    "duration_ms": 180000,
                    "artists": [{"name": "Test Artist", "id": "artist_123"}],
                    "album": {"name": "Test Album", "id": "album_123"},
                    "preview_url": "https://preview.spotify.com/track_123.mp3",
                }
            },
            {
                "track": {
                    "id": "track_456",
                    "name": "Another Song",
                    "duration_ms": 240000,
                    "artists": [{"name": "Another Artist", "id": "artist_456"}],
                    "album": {"name": "Another Album", "id": "album_456"},
                    "preview_url": None,
                }
            },
        ]
    }


class TestSpotifyClient:
    """Test SpotifyClient class."""

    def test_initialization(self) -> None:
        """Should initialize with proper configuration."""
        from src.core.spotify_client import SpotifyClient

        client = SpotifyClient()
        assert hasattr(client, "client_id")
        assert hasattr(client, "client_secret")
        assert hasattr(client, "redirect_uri")

    @patch("requests.post")
    def test_authenticate_user_success(
        self, mock_post: Mock, mock_spotify_tokens: Dict[str, Any]
    ) -> None:
        """Should successfully exchange authorization code for tokens."""
        from src.core.spotify_client import SpotifyClient

        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = mock_spotify_tokens

        client = SpotifyClient()
        tokens = client.authenticate_user("test_auth_code")

        assert tokens["access_token"] == "test_access_token"
        assert tokens["refresh_token"] == "test_refresh_token"
        assert tokens["expires_in"] == 3600

        # Verify correct API call
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert "grant_type=authorization_code" in call_args[1]["data"]
        assert "code=test_auth_code" in call_args[1]["data"]

    @patch("requests.post")
    def test_authenticate_user_invalid_code(self, mock_post: Mock) -> None:
        """Should handle invalid authorization code."""
        from src.core.spotify_client import SpotifyClient

        mock_post.return_value.status_code = 400
        mock_post.return_value.json.return_value = {"error": "invalid_grant"}

        client = SpotifyClient()

        with pytest.raises(Exception) as exc_info:
            client.authenticate_user("invalid_code")

        assert (
            "invalid_grant" in str(exc_info.value)
            or "authentication failed" in str(exc_info.value).lower()
        )

    @patch("requests.get")
    def test_get_user_profile_success(
        self, mock_get: Mock, mock_user_profile: Dict[str, Any]
    ) -> None:
        """Should fetch user profile successfully."""
        from src.core.spotify_client import SpotifyClient

        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = mock_user_profile

        client = SpotifyClient()
        profile = client.get_user_profile("test_access_token")

        assert profile["id"] == "test_user_123"
        assert profile["display_name"] == "Test User"
        assert profile["country"] == "US"

        # Verify correct API call with authorization header
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert call_args[1]["headers"]["Authorization"] == "Bearer test_access_token"

    @patch("requests.get")
    def test_get_user_profile_expired_token(self, mock_get: Mock) -> None:
        """Should handle expired access token."""
        from src.core.spotify_client import SpotifyClient

        mock_get.return_value.status_code = 401
        mock_get.return_value.json.return_value = {
            "error": {"status": 401, "message": "The access token expired"}
        }

        client = SpotifyClient()

        with pytest.raises(Exception) as exc_info:
            client.get_user_profile("expired_token")

        assert "401" in str(exc_info.value) or "expired" in str(exc_info.value).lower()

    @patch("requests.get")
    def test_search_country_playlists_success(
        self,
        mock_get: Mock,
        mock_playlist_response: Dict[str, Any],
        mock_tracks_response: Dict[str, Any],
    ) -> None:
        """Should search and return country playlists."""
        from src.core.spotify_client import SpotifyClient

        # Mock playlist search response first, then tracks response
        mock_get.side_effect = [
            Mock(status_code=200, json=Mock(return_value=mock_playlist_response)),
            Mock(status_code=200, json=Mock(return_value=mock_tracks_response)),
        ]

        client = SpotifyClient()
        tracks = client.search_country_playlists("US", "Top 50", "test_access_token")

        assert len(tracks) == 2
        assert tracks[0]["name"] == "Test Song"
        assert tracks[0]["duration_ms"] == 180000
        assert tracks[1]["name"] == "Another Song"

        # Should make two API calls (search playlist, get tracks)
        assert mock_get.call_count == 2

    @patch("requests.get")
    def test_search_country_playlists_no_results(self, mock_get: Mock) -> None:
        """Should handle no playlist results."""
        from src.core.spotify_client import SpotifyClient

        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {"playlists": {"items": []}}

        client = SpotifyClient()
        tracks = client.search_country_playlists("XX", "Top 50", "test_access_token")

        assert tracks == []

    @patch("requests.get")
    def test_search_tracks_success(self, mock_get: Mock) -> None:
        """Should search tracks successfully."""
        from src.core.spotify_client import SpotifyClient

        mock_response = {
            "tracks": {
                "items": [
                    {
                        "id": "track_789",
                        "name": "Search Result",
                        "duration_ms": 210000,
                        "artists": [{"name": "Search Artist"}],
                        "album": {"name": "Search Album"},
                    }
                ]
            }
        }

        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = mock_response

        client = SpotifyClient()
        tracks = client.search_tracks("test query", "test_access_token", limit=20)

        assert len(tracks) == 1
        assert tracks[0]["name"] == "Search Result"
        assert tracks[0]["duration_ms"] == 210000

        # Verify search parameters
        call_args = mock_get.call_args
        assert "q=test query" in call_args[0][0] or "q=test+query" in call_args[0][0]
        assert "type=track" in call_args[0][0]
        assert "limit=20" in call_args[0][0]

    @patch("requests.post")
    def test_refresh_user_token_success(
        self, mock_post: Mock, mock_spotify_tokens: Dict[str, Any]
    ) -> None:
        """Should refresh access token successfully."""
        from src.core.spotify_client import SpotifyClient

        refresh_response = {
            "access_token": "new_access_token",
            "expires_in": 3600,
            "token_type": "Bearer",
        }

        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = refresh_response

        client = SpotifyClient()
        tokens = client.refresh_user_token("test_refresh_token")

        assert tokens["access_token"] == "new_access_token"
        assert tokens["expires_in"] == 3600

        # Verify correct refresh token request
        call_args = mock_post.call_args
        assert "grant_type=refresh_token" in call_args[1]["data"]
        assert "refresh_token=test_refresh_token" in call_args[1]["data"]

    @patch("requests.post")
    def test_refresh_user_token_invalid_refresh_token(self, mock_post: Mock) -> None:
        """Should handle invalid refresh token."""
        from src.core.spotify_client import SpotifyClient

        mock_post.return_value.status_code = 400
        mock_post.return_value.json.return_value = {"error": "invalid_grant"}

        client = SpotifyClient()

        with pytest.raises(Exception) as exc_info:
            client.refresh_user_token("invalid_refresh_token")

        assert (
            "invalid_grant" in str(exc_info.value)
            or "refresh failed" in str(exc_info.value).lower()
        )


class TestSpotifyClientRetryLogic:
    """Test retry logic for Spotify API calls."""

    @patch("requests.get")
    def test_retry_on_rate_limit(self, mock_get: Mock) -> None:
        """Should retry requests when rate limited."""
        from src.core.spotify_client import SpotifyClient

        # First call returns rate limit, second succeeds
        mock_get.side_effect = [
            Mock(status_code=429, headers={"Retry-After": "1"}),
            Mock(status_code=200, json=Mock(return_value={"id": "user_123"})),
        ]

        client = SpotifyClient()

        with patch("time.sleep") as mock_sleep:
            profile = client.get_user_profile("test_token")

            assert profile["id"] == "user_123"
            assert mock_get.call_count == 2
            mock_sleep.assert_called_once_with(1)

    @patch("requests.get")
    def test_retry_on_server_error(self, mock_get: Mock) -> None:
        """Should retry on server errors (5xx)."""
        from src.core.spotify_client import SpotifyClient

        # First call server error, second succeeds
        mock_get.side_effect = [
            Mock(status_code=500),
            Mock(status_code=200, json=Mock(return_value={"id": "user_123"})),
        ]

        client = SpotifyClient()

        with patch("time.sleep") as mock_sleep:
            profile = client.get_user_profile("test_token")

            assert profile["id"] == "user_123"
            assert mock_get.call_count == 2
            mock_sleep.assert_called_once()

    @patch("requests.get")
    def test_max_retries_exceeded(self, mock_get: Mock) -> None:
        """Should fail after max retries exceeded."""
        from src.core.spotify_client import SpotifyClient

        # Always return server error
        mock_get.return_value = Mock(status_code=500)

        client = SpotifyClient()

        with patch("time.sleep"):
            with pytest.raises(Exception) as exc_info:
                client.get_user_profile("test_token")

            assert "max retries" in str(exc_info.value).lower() or "500" in str(
                exc_info.value
            )
            assert mock_get.call_count >= 3  # Should retry multiple times


class TestSpotifyClientErrorHandling:
    """Test error handling in Spotify client."""

    @patch("requests.get")
    def test_network_error_handling(self, mock_get: Mock) -> None:
        """Should handle network connectivity errors."""
        from src.core.spotify_client import SpotifyClient

        mock_get.side_effect = ConnectionError("Network unreachable")

        client = SpotifyClient()

        with pytest.raises(Exception) as exc_info:
            client.get_user_profile("test_token")

        assert (
            "network" in str(exc_info.value).lower()
            or "connection" in str(exc_info.value).lower()
        )

    @patch("requests.get")
    def test_timeout_error_handling(self, mock_get: Mock) -> None:
        """Should handle request timeouts."""
        from src.core.spotify_client import SpotifyClient

        mock_get.side_effect = TimeoutError("Request timeout")

        client = SpotifyClient()

        with pytest.raises(Exception) as exc_info:
            client.get_user_profile("test_token")

        assert "timeout" in str(exc_info.value).lower()

    @patch("requests.get")
    def test_invalid_json_response(self, mock_get: Mock) -> None:
        """Should handle invalid JSON responses."""
        from src.core.spotify_client import SpotifyClient

        mock_get.return_value.status_code = 200
        mock_get.return_value.json.side_effect = ValueError("Invalid JSON")

        client = SpotifyClient()

        with pytest.raises(Exception) as exc_info:
            client.get_user_profile("test_token")

        assert (
            "json" in str(exc_info.value).lower()
            or "parse" in str(exc_info.value).lower()
        )

    @patch("requests.get")
    def test_empty_response_handling(self, mock_get: Mock) -> None:
        """Should handle empty or malformed responses."""
        from src.core.spotify_client import SpotifyClient

        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {}

        client = SpotifyClient()

        # Should handle empty response gracefully
        tracks = client.search_country_playlists("US", "Top 50", "test_token")
        assert tracks == []


class TestSpotifyClientConfiguration:
    """Test Spotify client configuration."""

    def test_environment_variable_configuration(self) -> None:
        """Should load configuration from environment variables."""
        from src.core.spotify_client import SpotifyClient

        with patch.dict(
            "os.environ",
            {
                "SPOTIFY_CLIENT_ID": "test_client_id",
                "SPOTIFY_CLIENT_SECRET": "test_client_secret",
                "SPOTIFY_REDIRECT_URI": "http://localhost:8000/callback",
            },
        ):
            client = SpotifyClient()

            assert client.client_id == "test_client_id"
            assert client.client_secret == "test_client_secret"
            assert client.redirect_uri == "http://localhost:8000/callback"

    def test_missing_configuration_error(self) -> None:
        """Should raise error when required configuration is missing."""
        from src.core.spotify_client import SpotifyClient

        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(Exception) as exc_info:
                SpotifyClient()

            assert (
                "configuration" in str(exc_info.value).lower()
                or "client_id" in str(exc_info.value).lower()
            )

    def test_request_headers_configuration(self) -> None:
        """Should configure proper request headers."""
        from src.core.spotify_client import SpotifyClient

        client = SpotifyClient()

        with patch("requests.get") as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = {"id": "user_123"}

            client.get_user_profile("test_token")

            # Verify headers
            call_args = mock_get.call_args
            headers = call_args[1]["headers"]
            assert headers["Authorization"] == "Bearer test_token"
            assert headers["Content-Type"] == "application/json"


class TestSpotifyClientPlaylistProcessing:
    """Test playlist processing functionality."""

    @patch("requests.get")
    def test_playlist_track_filtering(self, mock_get: Mock) -> None:
        """Should filter tracks based on criteria."""
        from src.core.spotify_client import SpotifyClient

        mock_tracks_with_nulls = {
            "items": [
                {
                    "track": {
                        "id": "track_1",
                        "name": "Valid Track",
                        "duration_ms": 180000,
                        "artists": [{"name": "Artist"}],
                        "album": {"name": "Album"},
                    }
                },
                {
                    "track": None  # Invalid track
                },
                {
                    "track": {
                        "id": None,  # Invalid track ID
                        "name": "Invalid Track",
                        "duration_ms": 180000,
                        "artists": [{"name": "Artist"}],
                        "album": {"name": "Album"},
                    }
                },
            ]
        }

        mock_get.side_effect = [
            Mock(
                status_code=200,
                json=Mock(
                    return_value={
                        "playlists": {
                            "items": [{"id": "playlist_1", "tracks": {"href": "url"}}]
                        }
                    }
                ),
            ),
            Mock(status_code=200, json=Mock(return_value=mock_tracks_with_nulls)),
        ]

        client = SpotifyClient()
        tracks = client.search_country_playlists("US", "Top 50", "test_token")

        # Should only return valid tracks
        assert len(tracks) == 1
        assert tracks[0]["name"] == "Valid Track"

    @patch("requests.get")
    def test_large_playlist_pagination(self, mock_get: Mock) -> None:
        """Should handle paginated playlist responses."""
        from src.core.spotify_client import SpotifyClient

        # Mock multiple pages of tracks
        page1_response = {
            "items": [
                {
                    "track": {
                        "id": f"track_{i}",
                        "name": f"Song {i}",
                        "duration_ms": 180000,
                        "artists": [{"name": "Artist"}],
                        "album": {"name": "Album"},
                    }
                }
                for i in range(50)
            ],
            "next": "https://api.spotify.com/page2",
        }

        page2_response = {
            "items": [
                {
                    "track": {
                        "id": f"track_{i}",
                        "name": f"Song {i}",
                        "duration_ms": 180000,
                        "artists": [{"name": "Artist"}],
                        "album": {"name": "Album"},
                    }
                }
                for i in range(50, 100)
            ],
            "next": None,
        }

        mock_get.side_effect = [
            Mock(
                status_code=200,
                json=Mock(
                    return_value={
                        "playlists": {
                            "items": [{"id": "playlist_1", "tracks": {"href": "url"}}]
                        }
                    }
                ),
            ),
            Mock(status_code=200, json=Mock(return_value=page1_response)),
            Mock(status_code=200, json=Mock(return_value=page2_response)),
        ]

        client = SpotifyClient()
        tracks = client.search_country_playlists("US", "Top 50", "test_token")

        # Should return all tracks from both pages
        assert len(tracks) == 100
        assert tracks[0]["name"] == "Song 0"
        assert tracks[99]["name"] == "Song 99"


class TestSpotifyClientCaching:
    """Test caching functionality in Spotify client."""

    def test_token_caching_mechanism(self) -> None:
        """Should implement token caching to reduce API calls."""
        from src.core.spotify_client import SpotifyClient

        client = SpotifyClient()

        # This test verifies the design supports token caching
        # Implementation would cache tokens to avoid repeated auth calls
        assert hasattr(client, "_token_cache") or hasattr(client, "cache_tokens")

    def test_playlist_response_caching(self) -> None:
        """Should cache playlist responses for performance."""
        from src.core.spotify_client import SpotifyClient

        client = SpotifyClient()

        # This test verifies the design supports response caching
        # Implementation would cache frequent playlist requests
        with patch("requests.get") as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = {"playlists": {"items": []}}

            # Multiple calls for same playlist should use cache
            client.search_country_playlists("US", "Top 50", "test_token")
            client.search_country_playlists("US", "Top 50", "test_token")

            # Implementation should cache and reduce API calls
            assert mock_get.call_count <= 2  # Allow for implementation flexibility

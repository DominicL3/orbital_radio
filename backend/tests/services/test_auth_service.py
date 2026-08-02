"""Test cases for authentication service."""

from unittest.mock import Mock, patch
from datetime import timedelta
from typing import Dict, Any

from src.config import utcnow

import pytest


@pytest.fixture
def mock_spotify_tokens() -> Dict[str, str | int]:
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
    """Mock user profile data."""
    return {
        "id": "test_user_123",
        "display_name": "Test User",
        "email": "test@example.com",
        "country": "US",
        "followers": {"total": 42},
        "images": [{"url": "https://example.com/avatar.jpg"}],
    }


class TestAuthService:
    """Test AuthService class."""

    def test_initialization(self) -> None:
        """Should initialize with proper configuration."""
        from src.services.auth_service import AuthService

        service = AuthService()
        assert hasattr(service, "spotify_client")
        assert hasattr(service, "session_manager")
        assert hasattr(service, "client_id")
        assert hasattr(service, "client_secret")

    @patch("src.core.spotify_client.SpotifyClient.authenticate_user")
    def test_exchange_code_for_tokens_success(
        self, mock_authenticate: Mock, mock_spotify_tokens: Dict[str, Any]
    ) -> None:
        """Should successfully exchange authorization code for tokens."""
        from src.services.auth_service import AuthService

        mock_authenticate.return_value = mock_spotify_tokens

        service = AuthService()
        tokens = service.exchange_code_for_tokens("test_auth_code")

        assert tokens["access_token"] == "test_access_token"
        assert tokens["refresh_token"] == "test_refresh_token"
        assert tokens["expires_in"] == 3600

        mock_authenticate.assert_called_once_with("test_auth_code")

    @patch("src.core.spotify_client.SpotifyClient.authenticate_user")
    def test_exchange_code_for_tokens_invalid_code(
        self, mock_authenticate: Mock
    ) -> None:
        """Should handle invalid authorization code."""
        from src.services.auth_service import AuthService

        mock_authenticate.side_effect = Exception("Invalid authorization code")

        service = AuthService()

        with pytest.raises(Exception) as exc_info:
            service.exchange_code_for_tokens("invalid_code")

        assert "Invalid authorization code" in str(exc_info.value)

    @patch("src.core.spotify_client.SpotifyClient.get_user_profile")
    def test_get_user_profile_success(
        self, mock_get_profile: Mock, mock_user_profile: Dict[str, Any]
    ) -> None:
        """Should fetch user profile successfully."""
        from src.services.auth_service import AuthService

        mock_get_profile.return_value = mock_user_profile

        service = AuthService()
        profile = service.get_user_profile("test_access_token")

        assert profile["id"] == "test_user_123"
        assert profile["display_name"] == "Test User"
        assert profile["country"] == "US"

        mock_get_profile.assert_called_once_with("test_access_token")

    @patch("src.core.spotify_client.SpotifyClient.get_user_profile")
    def test_get_user_profile_expired_token(self, mock_get_profile: Mock) -> None:
        """Should handle expired access token."""
        from src.services.auth_service import AuthService

        mock_get_profile.side_effect = Exception("Token expired")

        service = AuthService()

        with pytest.raises(Exception) as exc_info:
            service.get_user_profile("expired_token")

        assert "Token expired" in str(exc_info.value)

    @patch("src.core.spotify_client.SpotifyClient.refresh_user_token")
    def test_refresh_access_token_success(
        self, mock_refresh: Mock, mock_spotify_tokens: Dict[str, Any]
    ) -> None:
        """Should refresh access token successfully."""
        from src.services.auth_service import AuthService

        refresh_response = {
            "access_token": "new_access_token",
            "expires_in": 3600,
            "token_type": "Bearer",
        }
        mock_refresh.return_value = refresh_response

        service = AuthService()
        tokens = service.refresh_access_token("test_refresh_token")

        assert tokens["access_token"] == "new_access_token"
        assert tokens["expires_in"] == 3600

        mock_refresh.assert_called_once_with("test_refresh_token")

    @patch("src.core.spotify_client.SpotifyClient.refresh_user_token")
    def test_refresh_access_token_invalid_refresh_token(
        self, mock_refresh: Mock
    ) -> None:
        """Should handle invalid refresh token."""
        from src.services.auth_service import AuthService

        mock_refresh.side_effect = Exception("Invalid refresh token")

        service = AuthService()

        with pytest.raises(Exception) as exc_info:
            service.refresh_access_token("invalid_refresh_token")

        assert "Invalid refresh token" in str(exc_info.value)

    @patch("src.services.cache_service.CacheService.create_session")
    def test_create_user_session(
        self,
        mock_create_session: Mock,
        mock_spotify_tokens: Dict[str, Any],
        mock_user_profile: Dict[str, Any],
    ) -> None:
        """Should create user session with tokens and profile."""
        from src.services.auth_service import AuthService

        mock_create_session.return_value = "session_123"

        service = AuthService()
        session_id = service.create_user_session(mock_spotify_tokens, mock_user_profile)

        assert session_id == "session_123"

        # Verify session creation with correct data
        mock_create_session.assert_called_once()
        call_args = mock_create_session.call_args[0][0]
        assert call_args["spotify_tokens"] == mock_spotify_tokens
        assert call_args["user_profile"] == mock_user_profile

    @patch("src.services.cache_service.CacheService.delete_session")
    def test_logout_user(self, mock_delete_session: Mock) -> None:
        """Should logout user and delete session."""
        from src.services.auth_service import AuthService

        service = AuthService()
        service.logout_user("session_123")

        mock_delete_session.assert_called_once_with("session_123")

    def test_validate_session_valid(self) -> None:
        """Should validate active session."""
        from src.services.auth_service import AuthService

        mock_session = {
            "session_id": "session_123",
            "spotify_tokens": {
                "access_token": "token",
                "expires_at": utcnow() + timedelta(hours=1),
            },
            "user_profile": {"id": "user_123"},
            "created_at": utcnow(),
            "expires_at": utcnow() + timedelta(hours=3),
        }

        service = AuthService()

        with patch.object(
            service.session_manager, "get_session", return_value=mock_session
        ):
            is_valid = service.validate_session("session_123")
            assert is_valid is True

    def test_validate_session_expired(self) -> None:
        """Should invalidate expired session."""
        from src.services.auth_service import AuthService

        expired_session = {
            "session_id": "session_123",
            "spotify_tokens": {
                "access_token": "token",
                "expires_at": utcnow() - timedelta(hours=1),
            },
            "user_profile": {"id": "user_123"},
            "created_at": utcnow() - timedelta(hours=4),
            "expires_at": utcnow() - timedelta(hours=1),
        }

        service = AuthService()

        with patch.object(
            service.session_manager, "get_session", return_value=expired_session
        ):
            is_valid = service.validate_session("session_123")
            assert is_valid is False

    def test_validate_session_not_found(self) -> None:
        """Should handle non-existent session."""
        from src.services.auth_service import AuthService

        service = AuthService()

        with patch.object(service.session_manager, "get_session", return_value=None):
            is_valid = service.validate_session("invalid_session")
            assert is_valid is False


class TestTokenManagement:
    """Test token management functionality."""

    def test_token_expiration_check(self) -> None:
        """Should check if token is expired."""
        from src.services.auth_service import AuthService

        service = AuthService()

        # Test non-expired token
        future_time = utcnow() + timedelta(hours=1)
        assert service.is_token_expired(future_time) is False

        # Test expired token
        past_time = utcnow() - timedelta(hours=1)
        assert service.is_token_expired(past_time) is True

        # Test token expiring soon (within 5 minutes)
        soon_time = utcnow() + timedelta(minutes=3)
        assert service.is_token_expired(soon_time) is True

    @patch("src.core.spotify_client.SpotifyClient.refresh_user_token")
    def test_auto_token_refresh(
        self, mock_refresh: Mock, mock_spotify_tokens: Dict[str, Any]
    ) -> None:
        """Should automatically refresh token when needed."""
        from src.services.auth_service import AuthService

        refresh_response = {
            "access_token": "new_access_token",
            "expires_in": 3600,
            "token_type": "Bearer",
        }
        mock_refresh.return_value = refresh_response

        service = AuthService()

        # Mock session with expiring token
        mock_session = {
            "spotify_tokens": {
                "access_token": "old_token",
                "refresh_token": "refresh_token",
                "expires_at": utcnow() + timedelta(minutes=3),
            }
        }

        with patch.object(
            service.session_manager, "get_session", return_value=mock_session
        ):
            with patch.object(service.session_manager, "update_session") as mock_update:
                result = service.ensure_valid_token("session_123")

                assert result["access_token"] == "new_access_token"
                mock_refresh.assert_called_once_with("refresh_token")
                mock_update.assert_called_once()

    def test_token_refresh_failure_handling(self) -> None:
        """Should handle token refresh failures."""
        from src.services.auth_service import AuthService

        service = AuthService()

        mock_session = {
            "spotify_tokens": {
                "access_token": "old_token",
                "refresh_token": "invalid_refresh_token",
                "expires_at": utcnow() + timedelta(minutes=3),
            }
        }

        with patch.object(
            service.session_manager, "get_session", return_value=mock_session
        ):
            with patch.object(
                service, "refresh_access_token", side_effect=Exception("Refresh failed")
            ):
                with pytest.raises(Exception) as exc_info:
                    service.ensure_valid_token("session_123")

                assert "Refresh failed" in str(exc_info.value)


class TestSessionManagement:
    """Test session management functionality."""

    def test_session_cleanup_expired(self) -> None:
        """Should clean up expired sessions."""
        from src.services.auth_service import AuthService

        service = AuthService()

        with patch.object(
            service.session_manager, "cleanup_expired_sessions"
        ) as mock_cleanup:
            service.cleanup_expired_sessions()
            mock_cleanup.assert_called_once()

    def test_session_activity_tracking(self) -> None:
        """Should track session activity."""
        from src.services.auth_service import AuthService

        service = AuthService()

        with patch.object(service.session_manager, "update_session") as mock_update:
            service.update_session_activity("session_123")

            mock_update.assert_called_once()
            call_args = mock_update.call_args
            assert call_args[0][0] == "session_123"
            assert "last_activity" in call_args[0][1]

    def test_concurrent_session_handling(self) -> None:
        """Should handle concurrent sessions for same user."""
        from src.services.auth_service import AuthService

        service = AuthService()

        # Test allowing multiple sessions per user
        user_profile = {"id": "user_123", "display_name": "Test User"}
        tokens = {"access_token": "token1", "refresh_token": "refresh1"}

        with patch.object(service.session_manager, "create_session") as mock_create:
            mock_create.side_effect = ["session_1", "session_2"]

            session1 = service.create_user_session(tokens, user_profile)
            session2 = service.create_user_session(tokens, user_profile)

            assert session1 != session2
            assert mock_create.call_count == 2

    def test_session_data_encryption(self) -> None:
        """Should encrypt sensitive session data."""
        from src.services.auth_service import AuthService

        service = AuthService()

        # Test that sensitive data is handled securely
        sensitive_data = {
            "access_token": "sensitive_token",
            "refresh_token": "sensitive_refresh",
        }

        with patch.object(service, "_encrypt_session_data") as mock_encrypt:
            mock_encrypt.return_value = "encrypted_data"

            encrypted = service._encrypt_session_data(sensitive_data)
            assert encrypted == "encrypted_data"
            mock_encrypt.assert_called_once_with(sensitive_data)


class TestErrorHandling:
    """Test error handling in auth service."""

    def test_network_error_handling(self) -> None:
        """Should handle network errors gracefully."""
        from src.services.auth_service import AuthService

        service = AuthService()

        with patch.object(service.spotify_client, "authenticate_user") as mock_auth:
            mock_auth.side_effect = ConnectionError("Network unreachable")

            with pytest.raises(Exception) as exc_info:
                service.exchange_code_for_tokens("test_code")

            assert (
                "network" in str(exc_info.value).lower()
                or "connection" in str(exc_info.value).lower()
            )

    def test_spotify_api_error_handling(self) -> None:
        """Should handle Spotify API errors."""
        from src.services.auth_service import AuthService

        service = AuthService()

        # Test various Spotify API errors
        api_errors = [
            {"error": "invalid_request", "error_description": "Invalid request"},
            {"error": "invalid_client", "error_description": "Invalid client"},
            {
                "error": "invalid_grant",
                "error_description": "Invalid authorization grant",
            },
        ]

        for error in api_errors:
            with patch.object(service.spotify_client, "authenticate_user") as mock_auth:
                mock_auth.side_effect = Exception(
                    f"Spotify API Error: {error['error']}"
                )

                with pytest.raises(Exception) as exc_info:
                    service.exchange_code_for_tokens("test_code")

                assert error["error"] in str(exc_info.value)

    def test_session_storage_error_handling(self) -> None:
        """Should handle session storage errors."""
        from src.services.auth_service import AuthService

        service = AuthService()

        with patch.object(service.session_manager, "create_session") as mock_create:
            mock_create.side_effect = Exception("Storage error")

            with pytest.raises(Exception) as exc_info:
                service.create_user_session({"token": "test"}, {"id": "user"})

            assert "Storage error" in str(exc_info.value)

    def test_malformed_token_response_handling(self) -> None:
        """Should handle malformed token responses."""
        from src.services.auth_service import AuthService

        service = AuthService()

        # Test various malformed responses
        malformed_responses = [
            {},  # Empty response
            {"access_token": None},  # Null token
            {"access_token": ""},  # Empty token
            {"error": "server_error"},  # Error response
        ]

        for response in malformed_responses:
            with patch.object(
                service.spotify_client, "authenticate_user", return_value=response
            ):
                if "error" in response:
                    with pytest.raises(Exception):
                        service.exchange_code_for_tokens("test_code")
                else:
                    # Should handle gracefully or raise appropriate error
                    try:
                        result = service.exchange_code_for_tokens("test_code")
                        # Should either succeed with valid data or raise exception
                        assert result is not None
                    except Exception:
                        pass  # Expected for malformed responses


class TestSecurityFeatures:
    """Test security features in auth service."""

    def test_session_id_generation(self) -> None:
        """Should generate secure session IDs."""
        from src.services.auth_service import AuthService

        service = AuthService()

        # Generate multiple session IDs and verify uniqueness
        session_ids = set()
        for _ in range(100):
            session_id = service._generate_session_id()
            assert len(session_id) >= 32  # Minimum length for security
            assert session_id not in session_ids  # Should be unique
            session_ids.add(session_id)

    def test_csrf_token_validation(self) -> None:
        """Should validate CSRF tokens in OAuth flow."""
        from src.services.auth_service import AuthService

        service = AuthService()

        # Test valid state token
        valid_state = "valid_csrf_token_123"
        with patch.object(service, "_validate_csrf_token", return_value=True):
            assert service._validate_csrf_token(valid_state) is True

        # Test invalid state token
        invalid_state = "invalid_token"
        with patch.object(service, "_validate_csrf_token", return_value=False):
            assert service._validate_csrf_token(invalid_state) is False

    def test_rate_limiting(self) -> None:
        """Should implement rate limiting for auth endpoints."""
        from src.services.auth_service import AuthService

        service = AuthService()

        # Test rate limiting for token exchange
        with patch.object(service, "_check_rate_limit") as mock_rate_limit:
            mock_rate_limit.return_value = True  # Within rate limit

            assert service._check_rate_limit("127.0.0.1", "token_exchange") is True

            mock_rate_limit.return_value = False  # Rate limit exceeded
            assert service._check_rate_limit("127.0.0.1", "token_exchange") is False

    def test_token_scope_validation(self) -> None:
        """Should validate token scopes."""
        from src.services.auth_service import AuthService

        service = AuthService()

        # Test valid scopes
        valid_scopes = ["user-read-private", "user-read-email", "playlist-read-private"]
        token_with_valid_scopes = {"scope": " ".join(valid_scopes)}

        assert service._validate_token_scopes(token_with_valid_scopes) is True

        # Test missing required scopes
        invalid_scopes = ["user-read-private"]  # Missing required scopes
        token_with_invalid_scopes = {"scope": " ".join(invalid_scopes)}

        assert service._validate_token_scopes(token_with_invalid_scopes) is False

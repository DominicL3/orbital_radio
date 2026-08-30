"""Test cases for user Pydantic schemas."""

import pytest
from pydantic import ValidationError

from src.config import utcnow


class TestUserSchemas:
    """Test user-related Pydantic schemas."""

    def test_user_create_schema_valid(self) -> None:
        """Should validate UserCreate schema with valid data."""
        from src.schemas.user import UserCreate

        user_data = {
            "spotify_user_id": "spotify_user_123",
            "display_name": "Test User",
            "email": "test@example.com",
            "country": "US",
            "spotify_tokens": {
                "access_token": "access_token_123",
                "refresh_token": "refresh_token_123",
                "expires_in": 3600,
                "token_type": "Bearer",
                "scope": "user-read-private user-read-email",
            },
        }

        user_create = UserCreate(**user_data)

        assert user_create.spotify_user_id == "spotify_user_123"
        assert user_create.display_name == "Test User"
        assert user_create.email == "test@example.com"
        assert user_create.country == "US"
        assert user_create.spotify_tokens.access_token == "access_token_123"

    def test_user_create_schema_missing_required_fields(self) -> None:
        """Should reject UserCreate with missing required fields."""
        from src.schemas.user import UserCreate

        # Missing spotify_user_id
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(display_name="Test User", email="test@example.com", country="US")

        assert "spotify_user_id" in str(exc_info.value)

        # Missing spotify_tokens
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(
                spotify_user_id="spotify_user_123",
                display_name="Test User",
                email="test@example.com",
                country="US",
            )

        assert "spotify_tokens" in str(exc_info.value)

    def test_user_create_schema_email_validation(self) -> None:
        """Should validate email format in UserCreate."""
        from src.schemas.user import UserCreate

        valid_emails = [
            "test@example.com",
            "user.name@domain.org",
            "user+tag@subdomain.example.com",
        ]

        for email in valid_emails:
            user_create = UserCreate(
                spotify_user_id="user_123",
                display_name="Test User",
                email=email,
                country="US",
                spotify_tokens={
                    "access_token": "token",
                    "refresh_token": "refresh",
                    "expires_in": 3600,
                    "token_type": "Bearer",
                    "scope": "user-read-private",
                },
            )
            assert user_create.email == email

        # Invalid emails
        invalid_emails = [
            "invalid_email",
            "@example.com",
            "user@",
            "user space@example.com",
        ]

        for invalid_email in invalid_emails:
            with pytest.raises(ValidationError):
                UserCreate(
                    spotify_user_id="user_123",
                    display_name="Test User",
                    email=invalid_email,
                    country="US",
                    spotify_tokens={
                        "access_token": "token",
                        "refresh_token": "refresh",
                        "expires_in": 3600,
                        "token_type": "Bearer",
                        "scope": "user-read-private",
                    },
                )

    def test_user_create_schema_country_validation(self) -> None:
        """Should validate country code format."""
        from src.schemas.user import UserCreate

        valid_countries = ["US", "GB", "FR", "DE", "JP", "AU", "CA", "BR"]

        for country in valid_countries:
            user_create = UserCreate(
                spotify_user_id="user_123",
                display_name="Test User",
                email="test@example.com",
                country=country,
                spotify_tokens={
                    "access_token": "token",
                    "refresh_token": "refresh",
                    "expires_in": 3600,
                    "token_type": "Bearer",
                    "scope": "user-read-private",
                },
            )
            assert user_create.country == country

        # Invalid country codes
        invalid_countries = ["USA", "United States", "", "123", "ZZ"]

        for invalid_country in invalid_countries:
            with pytest.raises(ValidationError):
                UserCreate(
                    spotify_user_id="user_123",
                    display_name="Test User",
                    email="test@example.com",
                    country=invalid_country,
                    spotify_tokens={
                        "access_token": "token",
                        "refresh_token": "refresh",
                        "expires_in": 3600,
                        "token_type": "Bearer",
                        "scope": "user-read-private",
                    },
                )

    def test_user_response_schema(self) -> None:
        """Should validate UserResponse schema."""
        from src.schemas.user import UserResponse

        user_data = {
            "id": "user_123",
            "spotify_user_id": "spotify_user_123",
            "display_name": "Test User",
            "email": "test@example.com",
            "country": "US",
            "created_at": utcnow(),
            "last_login": utcnow(),
            "is_active": True,
        }

        user_response = UserResponse(**user_data)

        assert user_response.id == "user_123"
        assert user_response.spotify_user_id == "spotify_user_123"
        assert user_response.display_name == "Test User"
        assert user_response.is_active is True

        # Should not include sensitive data like tokens
        assert not hasattr(user_response, "spotify_tokens")
        assert not hasattr(user_response, "access_token")

    def test_user_update_schema(self) -> None:
        """Should validate UserUpdate schema."""
        from src.schemas.user import UserUpdate

        # All fields optional for update
        user_update = UserUpdate()
        assert user_update is not None

        # Partial update
        user_update = UserUpdate(display_name="Updated Name")
        assert user_update.display_name == "Updated Name"
        assert user_update.email is None  # Should be None if not provided

        # Full update
        user_update = UserUpdate(
            display_name="New Name", email="new@example.com", country="GB"
        )
        assert user_update.display_name == "New Name"
        assert user_update.email == "new@example.com"
        assert user_update.country == "GB"

    def test_user_update_schema_validation(self) -> None:
        """Should validate fields in UserUpdate schema."""
        from src.schemas.user import UserUpdate

        # Valid email update
        user_update = UserUpdate(email="new@example.com")
        assert user_update.email == "new@example.com"

        # Invalid email update
        with pytest.raises(ValidationError):
            UserUpdate(email="invalid_email")

        # Valid country update
        user_update = UserUpdate(country="FR")
        assert user_update.country == "FR"

        # Invalid country update
        with pytest.raises(ValidationError):
            UserUpdate(country="France")


class TestSpotifyTokensSchema:
    """Test Spotify tokens schema."""

    def test_spotify_tokens_schema_valid(self) -> None:
        """Should validate SpotifyTokens schema with valid data."""
        from src.schemas.user import SpotifyTokens

        tokens_data = {
            "access_token": "BQC4WK3CXYZ...",
            "refresh_token": "AQA7REF4MNO...",
            "expires_in": 3600,
            "token_type": "Bearer",
            "scope": "user-read-private user-read-email playlist-read-private",
        }

        tokens = SpotifyTokens(**tokens_data)

        assert tokens.access_token == "BQC4WK3CXYZ..."
        assert tokens.refresh_token == "AQA7REF4MNO..."
        assert tokens.expires_in == 3600
        assert tokens.token_type == "Bearer"
        assert "user-read-private" in tokens.scope

    def test_spotify_tokens_schema_missing_required(self) -> None:
        """Should reject SpotifyTokens with missing required fields."""
        from src.schemas.user import SpotifyTokens

        # Missing access_token
        with pytest.raises(ValidationError) as exc_info:
            SpotifyTokens(
                refresh_token="refresh_token",
                expires_in=3600,
                token_type="Bearer",
                scope="user-read-private",
            )

        assert "access_token" in str(exc_info.value)

        # Missing refresh_token
        with pytest.raises(ValidationError) as exc_info:
            SpotifyTokens(
                access_token="access_token",
                expires_in=3600,
                token_type="Bearer",
                scope="user-read-private",
            )

        assert "refresh_token" in str(exc_info.value)

    def test_spotify_tokens_schema_token_type_validation(self) -> None:
        """Should validate token_type field."""
        from src.schemas.user import SpotifyTokens

        # Valid token type
        tokens = SpotifyTokens(
            access_token="access_token",
            refresh_token="refresh_token",
            expires_in=3600,
            token_type="Bearer",
            scope="user-read-private",
        )
        assert tokens.token_type == "Bearer"

        # Invalid token type
        with pytest.raises(ValidationError):
            SpotifyTokens(
                access_token="access_token",
                refresh_token="refresh_token",
                expires_in=3600,
                token_type="Invalid",
                scope="user-read-private",
            )

    def test_spotify_tokens_schema_expires_in_validation(self) -> None:
        """Should validate expires_in field."""
        from src.schemas.user import SpotifyTokens

        # Valid expires_in values
        valid_expires_in = [3600, 7200, 1800]

        for expires_in in valid_expires_in:
            tokens = SpotifyTokens(
                access_token="access_token",
                refresh_token="refresh_token",
                expires_in=expires_in,
                token_type="Bearer",
                scope="user-read-private",
            )
            assert tokens.expires_in == expires_in

        # Invalid expires_in values
        invalid_expires_in = [-1, 0, "3600", None]

        for invalid_expires in invalid_expires_in:
            with pytest.raises(ValidationError):
                SpotifyTokens(
                    access_token="access_token",
                    refresh_token="refresh_token",
                    expires_in=invalid_expires,
                    token_type="Bearer",
                    scope="user-read-private",
                )

    def test_spotify_tokens_schema_scope_validation(self) -> None:
        """Should validate scope field contains required scopes."""
        from src.schemas.user import SpotifyTokens

        # Valid scope with all required permissions
        valid_scope = "user-read-private user-read-email playlist-read-private"
        tokens = SpotifyTokens(
            access_token="access_token",
            refresh_token="refresh_token",
            expires_in=3600,
            token_type="Bearer",
            scope=valid_scope,
        )
        assert tokens.scope == valid_scope

        # Missing required scopes
        invalid_scopes = [
            "user-read-private",  # Missing email and playlist
            "user-read-email",  # Missing private and playlist
            "",  # Empty scope
            "invalid-scope",  # Invalid scope
        ]

        for invalid_scope in invalid_scopes:
            with pytest.raises(ValidationError):
                SpotifyTokens(
                    access_token="access_token",
                    refresh_token="refresh_token",
                    expires_in=3600,
                    token_type="Bearer",
                    scope=invalid_scope,
                )


class TestUserProfileSchema:
    """Test user profile schema."""

    def test_user_profile_schema_valid(self) -> None:
        """Should validate UserProfile schema with valid data."""
        from src.schemas.user import UserProfile

        profile_data = {
            "id": "spotify_user_123",
            "display_name": "Test User",
            "email": "test@example.com",
            "country": "US",
            "followers": {"total": 42},
            "images": [
                {"url": "https://example.com/avatar.jpg", "height": 300, "width": 300}
            ],
            "external_urls": {
                "spotify": "https://open.spotify.com/user/spotify_user_123"
            },
        }

        profile = UserProfile(**profile_data)

        assert profile.id == "spotify_user_123"
        assert profile.display_name == "Test User"
        assert profile.email == "test@example.com"
        assert profile.country == "US"
        assert profile.followers["total"] == 42

    def test_user_profile_schema_optional_fields(self) -> None:
        """Should handle optional fields in UserProfile."""
        from src.schemas.user import UserProfile

        # Minimal profile data
        minimal_profile = {"id": "spotify_user_123", "display_name": "Test User"}

        profile = UserProfile(**minimal_profile)

        assert profile.id == "spotify_user_123"
        assert profile.display_name == "Test User"
        assert profile.email is None
        assert profile.country is None
        assert profile.followers is None
        assert profile.images is None

    def test_user_profile_schema_followers_validation(self) -> None:
        """Should validate followers field structure."""
        from src.schemas.user import UserProfile

        # Valid followers data
        profile = UserProfile(
            id="user_123", display_name="Test User", followers={"total": 100}
        )
        assert profile.followers["total"] == 100

        # Invalid followers data
        with pytest.raises(ValidationError):
            UserProfile(
                id="user_123", display_name="Test User", followers={"invalid": "data"}
            )

    def test_user_profile_schema_images_validation(self) -> None:
        """Should validate images field structure."""
        from src.schemas.user import UserProfile

        # Valid images data
        profile = UserProfile(
            id="user_123",
            display_name="Test User",
            images=[
                {"url": "https://example.com/image1.jpg", "height": 300, "width": 300},
                {"url": "https://example.com/image2.jpg", "height": 150, "width": 150},
            ],
        )
        assert len(profile.images) == 2
        assert profile.images[0]["url"] == "https://example.com/image1.jpg"

        # Invalid images data
        with pytest.raises(ValidationError):
            UserProfile(
                id="user_123", display_name="Test User", images=[{"invalid": "data"}]
            )


class TestUserSchemaIntegration:
    """Test integration between user schemas."""

    def test_user_create_to_response_conversion(self) -> None:
        """Should convert UserCreate to UserResponse."""
        from src.schemas.user import UserCreate, UserResponse

        user_create_data = {
            "spotify_user_id": "spotify_user_123",
            "display_name": "Test User",
            "email": "test@example.com",
            "country": "US",
            "spotify_tokens": {
                "access_token": "access_token",
                "refresh_token": "refresh_token",
                "expires_in": 3600,
                "token_type": "Bearer",
                "scope": "user-read-private user-read-email",
            },
        }

        user_create = UserCreate(**user_create_data)

        # Convert to response (excluding sensitive data)
        user_response_data = {
            "id": "generated_user_id",
            "spotify_user_id": user_create.spotify_user_id,
            "display_name": user_create.display_name,
            "email": user_create.email,
            "country": user_create.country,
            "created_at": utcnow(),
            "last_login": utcnow(),
            "is_active": True,
        }

        user_response = UserResponse(**user_response_data)

        assert user_response.spotify_user_id == user_create.spotify_user_id
        assert user_response.display_name == user_create.display_name
        assert user_response.email == user_create.email
        # Tokens should not be included in response
        assert not hasattr(user_response, "spotify_tokens")

    def test_schema_serialization(self) -> None:
        """Should serialize schemas to JSON correctly."""
        from src.schemas.user import UserResponse

        user_response = UserResponse(
            id="user_123",
            spotify_user_id="spotify_user_123",
            display_name="Test User",
            email="test@example.com",
            country="US",
            created_at=utcnow(),
            last_login=utcnow(),
            is_active=True,
        )

        # Should serialize to JSON
        json_data = user_response.model_dump_json()
        assert isinstance(json_data, str)
        assert "Test User" in json_data
        assert "user_123" in json_data

        # Should deserialize from JSON
        import json

        parsed_data = json.loads(json_data)
        assert parsed_data["display_name"] == "Test User"
        assert parsed_data["country"] == "US"

    def test_schema_field_aliases(self) -> None:
        """Should handle field aliases correctly."""
        from src.schemas.user import UserResponse

        # Test data with snake_case field names
        user_data = {
            "id": "user_123",
            "spotify_user_id": "spotify_user_123",
            "display_name": "Test User",
            "email": "test@example.com",
            "country": "US",
            "created_at": utcnow(),
            "last_login": utcnow(),
            "is_active": True,
        }

        user_response = UserResponse(**user_data)

        # Should serialize with correct field names
        serialized = user_response.model_dump()
        assert "spotify_user_id" in serialized
        assert "display_name" in serialized
        assert "created_at" in serialized

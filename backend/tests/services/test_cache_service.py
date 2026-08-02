"""Test cases for cache service."""

from unittest.mock import patch
from typing import Dict, Any
from datetime import datetime, timedelta

import pytest


@pytest.fixture
def mock_session_data() -> Dict[str, Any]:
    """Mock session data for testing."""
    return {
        "session_id": "session_123",
        "spotify_tokens": {
            "access_token": "test_access_token",
            "refresh_token": "test_refresh_token",
            "expires_at": datetime.utcnow() + timedelta(hours=1),
        },
        "user_profile": {
            "id": "user_123",
            "display_name": "Test User",
            "country": "US",
        },
        "orbital_session": {
            "satellite_id": "iss",
            "start_time": datetime.utcnow(),
            "played_tracks": {"track_1", "track_2"},
            "track_history": [],
        },
        "created_at": datetime.utcnow(),
        "expires_at": datetime.utcnow() + timedelta(hours=3),
        "last_activity": datetime.utcnow(),
    }


class TestCacheService:
    """Test CacheService class."""

    def test_initialization(self) -> None:
        """Should initialize with proper configuration."""
        from src.services.cache_service import CacheService

        cache_service = CacheService()
        assert hasattr(cache_service, "session_cache")
        assert hasattr(cache_service, "tle_cache")
        assert hasattr(cache_service, "playlist_cache")
        assert hasattr(cache_service, "max_session_size")

    def test_create_session(self, mock_session_data: Dict[str, Any]) -> None:
        """Should create new session and return session ID."""
        from src.services.cache_service import CacheService

        cache_service = CacheService()
        session_id = cache_service.create_session(mock_session_data)

        assert isinstance(session_id, str)
        assert len(session_id) >= 32  # Should be a UUID or similar

        # Session should be stored in cache
        stored_session = cache_service.get_session(session_id)
        assert stored_session is not None
        assert stored_session["user_profile"]["id"] == "user_123"

    def test_get_session_exists(self, mock_session_data: Dict[str, Any]) -> None:
        """Should retrieve existing session."""
        from src.services.cache_service import CacheService

        cache_service = CacheService()
        session_id = cache_service.create_session(mock_session_data)

        retrieved_session = cache_service.get_session(session_id)

        assert retrieved_session is not None
        assert retrieved_session["session_id"] == session_id
        assert retrieved_session["user_profile"]["display_name"] == "Test User"

    def test_get_session_not_exists(self) -> None:
        """Should return None for non-existent session."""
        from src.services.cache_service import CacheService

        cache_service = CacheService()
        session = cache_service.get_session("non_existent_session")

        assert session is None

    def test_update_session(self, mock_session_data: Dict[str, Any]) -> None:
        """Should update existing session data."""
        from src.services.cache_service import CacheService

        cache_service = CacheService()
        session_id = cache_service.create_session(mock_session_data)

        update_data = {
            "orbital_session": {
                "satellite_id": "noaa19",
                "played_tracks": {"track_3", "track_4"},
            },
            "last_activity": datetime.utcnow(),
        }

        cache_service.update_session(session_id, update_data)

        updated_session = cache_service.get_session(session_id)
        assert updated_session["orbital_session"]["satellite_id"] == "noaa19"
        assert "track_3" in updated_session["orbital_session"]["played_tracks"]

    def test_update_session_not_exists(self) -> None:
        """Should handle update of non-existent session."""
        from src.services.cache_service import CacheService

        cache_service = CacheService()

        with pytest.raises(ValueError) as exc_info:
            cache_service.update_session("non_existent", {"data": "test"})

        assert "session" in str(exc_info.value).lower()

    def test_delete_session(self, mock_session_data: Dict[str, Any]) -> None:
        """Should delete existing session."""
        from src.services.cache_service import CacheService

        cache_service = CacheService()
        session_id = cache_service.create_session(mock_session_data)

        # Verify session exists
        assert cache_service.get_session(session_id) is not None

        # Delete session
        cache_service.delete_session(session_id)

        # Verify session is deleted
        assert cache_service.get_session(session_id) is None

    def test_delete_session_not_exists(self) -> None:
        """Should handle deletion of non-existent session gracefully."""
        from src.services.cache_service import CacheService

        cache_service = CacheService()

        # Should not raise an error
        cache_service.delete_session("non_existent_session")


class TestSessionExpiration:
    """Test session expiration functionality."""

    def test_cleanup_expired_sessions(self) -> None:
        """Should remove expired sessions from cache."""
        from src.services.cache_service import CacheService

        cache_service = CacheService()

        # Create expired session
        expired_session = {
            "session_id": "expired_123",
            "user_profile": {"id": "user_123"},
            "created_at": datetime.utcnow() - timedelta(hours=5),
            "expires_at": datetime.utcnow() - timedelta(hours=1),
            "last_activity": datetime.utcnow() - timedelta(hours=2),
        }

        # Create active session
        active_session = {
            "session_id": "active_123",
            "user_profile": {"id": "user_456"},
            "created_at": datetime.utcnow(),
            "expires_at": datetime.utcnow() + timedelta(hours=2),
            "last_activity": datetime.utcnow(),
        }

        expired_id = cache_service.create_session(expired_session)
        active_id = cache_service.create_session(active_session)

        # Manually expire the session
        cache_service.session_cache[expired_id]["expires_at"] = (
            datetime.utcnow() - timedelta(hours=1)
        )

        # Run cleanup
        cache_service.cleanup_expired_sessions()

        # Expired session should be removed
        assert cache_service.get_session(expired_id) is None

        # Active session should remain
        assert cache_service.get_session(active_id) is not None

    def test_is_session_expired(self) -> None:
        """Should correctly identify expired sessions."""
        from src.services.cache_service import CacheService

        cache_service = CacheService()

        # Test expired session
        expired_session = {
            "expires_at": datetime.utcnow() - timedelta(hours=1),
            "last_activity": datetime.utcnow() - timedelta(hours=2),
        }

        assert cache_service._is_session_expired(expired_session) is True

        # Test active session
        active_session = {
            "expires_at": datetime.utcnow() + timedelta(hours=1),
            "last_activity": datetime.utcnow() - timedelta(minutes=30),
        }

        assert cache_service._is_session_expired(active_session) is False

    def test_extend_session_expiration(self, mock_session_data: Dict[str, Any]) -> None:
        """Should extend session expiration time."""
        from src.services.cache_service import CacheService

        cache_service = CacheService()
        session_id = cache_service.create_session(mock_session_data)

        original_expiry = cache_service.get_session(session_id)["expires_at"]

        # Extend session
        cache_service.extend_session_expiration(session_id, hours=2)

        updated_session = cache_service.get_session(session_id)
        new_expiry = updated_session["expires_at"]

        assert new_expiry > original_expiry
        assert (new_expiry - original_expiry) >= timedelta(hours=1, minutes=59)

    def test_auto_extend_on_activity(self, mock_session_data: Dict[str, Any]) -> None:
        """Should automatically extend session on activity."""
        from src.services.cache_service import CacheService

        cache_service = CacheService()
        session_id = cache_service.create_session(mock_session_data)

        original_activity = cache_service.get_session(session_id)["last_activity"]

        # Simulate activity
        cache_service.update_session_activity(session_id)

        updated_session = cache_service.get_session(session_id)
        new_activity = updated_session["last_activity"]

        assert new_activity > original_activity


class TestTLECaching:
    """Test TLE data caching functionality."""

    def test_cache_tle_data(self) -> None:
        """Should cache TLE data for satellites."""
        from src.services.cache_service import CacheService

        cache_service = CacheService()

        tle_data = {
            "satellite_id": "iss",
            "tle_line1": "1 25544U 98067A   21001.00000000  .00001234  00000-0  12345-4 0  9990",
            "tle_line2": "2 25544  51.6464 123.4567  0003456 123.4567 234.5678 15.49123456123456",
            "epoch": datetime.utcnow(),
            "last_updated": datetime.utcnow(),
        }

        cache_service.cache_tle_data("iss", tle_data)

        cached_data = cache_service.get_cached_tle_data("iss")
        assert cached_data is not None
        assert cached_data["satellite_id"] == "iss"
        assert cached_data["tle_line1"] == tle_data["tle_line1"]

    def test_get_cached_tle_data_not_found(self) -> None:
        """Should return None for non-cached TLE data."""
        from src.services.cache_service import CacheService

        cache_service = CacheService()
        cached_data = cache_service.get_cached_tle_data("unknown_satellite")

        assert cached_data is None

    def test_tle_data_freshness_check(self) -> None:
        """Should check TLE data freshness."""
        from src.services.cache_service import CacheService

        cache_service = CacheService()

        # Fresh TLE data
        fresh_tle = {
            "satellite_id": "iss",
            "last_updated": datetime.utcnow() - timedelta(hours=1),
            "epoch": datetime.utcnow() - timedelta(hours=2),
        }

        cache_service.cache_tle_data("iss", fresh_tle)
        assert cache_service.is_tle_data_fresh("iss", max_age_hours=6) is True

        # Stale TLE data
        stale_tle = {
            "satellite_id": "noaa19",
            "last_updated": datetime.utcnow() - timedelta(hours=25),
            "epoch": datetime.utcnow() - timedelta(hours=26),
        }

        cache_service.cache_tle_data("noaa19", stale_tle)
        assert cache_service.is_tle_data_fresh("noaa19", max_age_hours=6) is False

    def test_clear_stale_tle_data(self) -> None:
        """Should clear stale TLE data from cache."""
        from src.services.cache_service import CacheService

        cache_service = CacheService()

        # Add fresh and stale TLE data
        fresh_tle = {
            "satellite_id": "iss",
            "last_updated": datetime.utcnow() - timedelta(hours=1),
        }

        stale_tle = {
            "satellite_id": "noaa19",
            "last_updated": datetime.utcnow() - timedelta(hours=25),
        }

        cache_service.cache_tle_data("iss", fresh_tle)
        cache_service.cache_tle_data("noaa19", stale_tle)

        # Clear stale data
        cache_service.clear_stale_tle_data(max_age_hours=12)

        # Fresh data should remain
        assert cache_service.get_cached_tle_data("iss") is not None

        # Stale data should be removed
        assert cache_service.get_cached_tle_data("noaa19") is None


class TestPlaylistCaching:
    """Test playlist caching functionality."""

    def test_cache_playlist_data(self) -> None:
        """Should cache playlist data for regions."""
        from src.services.cache_service import CacheService

        cache_service = CacheService()

        playlist_data = {
            "region_code": "US",
            "playlist_type": "Top 50",
            "tracks": [
                {"id": "track_1", "name": "Song 1"},
                {"id": "track_2", "name": "Song 2"},
            ],
            "cached_at": datetime.utcnow(),
        }

        cache_key = "US_Top_50"
        cache_service.cache_playlist_data(cache_key, playlist_data)

        cached_playlist = cache_service.get_cached_playlist_data(cache_key)
        assert cached_playlist is not None
        assert cached_playlist["region_code"] == "US"
        assert len(cached_playlist["tracks"]) == 2

    def test_playlist_cache_expiration(self) -> None:
        """Should expire cached playlist data after TTL."""
        from src.services.cache_service import CacheService

        cache_service = CacheService()

        expired_playlist = {
            "region_code": "GB",
            "tracks": [{"id": "track_1", "name": "Song 1"}],
            "cached_at": datetime.utcnow() - timedelta(hours=25),
        }

        cache_key = "GB_Top_50"
        cache_service.cache_playlist_data(cache_key, expired_playlist)

        # Should return None for expired cache
        cached_data = cache_service.get_cached_playlist_data(cache_key, ttl_hours=12)
        assert cached_data is None

    def test_clear_playlist_cache(self) -> None:
        """Should clear all playlist cache data."""
        from src.services.cache_service import CacheService

        cache_service = CacheService()

        # Add multiple playlist entries
        cache_service.cache_playlist_data("US_Top_50", {"tracks": []})
        cache_service.cache_playlist_data("GB_Top_50", {"tracks": []})
        cache_service.cache_playlist_data("JP_Viral_50", {"tracks": []})

        # Clear cache
        cache_service.clear_playlist_cache()

        # All entries should be removed
        assert cache_service.get_cached_playlist_data("US_Top_50") is None
        assert cache_service.get_cached_playlist_data("GB_Top_50") is None
        assert cache_service.get_cached_playlist_data("JP_Viral_50") is None


class TestMemoryManagement:
    """Test memory management functionality."""

    def test_session_cache_size_limit(self) -> None:
        """Should limit session cache size to prevent memory issues."""
        from src.services.cache_service import CacheService

        cache_service = CacheService()
        cache_service.max_session_size = 5  # Set low limit for testing

        # Create more sessions than the limit
        session_ids = []
        for i in range(10):
            session_data = {
                "user_profile": {"id": f"user_{i}"},
                "created_at": datetime.utcnow(),
                "expires_at": datetime.utcnow() + timedelta(hours=3),
            }
            session_id = cache_service.create_session(session_data)
            session_ids.append(session_id)

        # Should not exceed the limit
        assert len(cache_service.session_cache) <= cache_service.max_session_size

        # Oldest sessions should be evicted
        assert cache_service.get_session(session_ids[0]) is None
        assert cache_service.get_session(session_ids[-1]) is not None

    def test_memory_usage_monitoring(self) -> None:
        """Should monitor memory usage of cache."""
        from src.services.cache_service import CacheService

        cache_service = CacheService()

        # Get initial memory usage
        initial_usage = cache_service.get_memory_usage()

        # Add data to cache
        for i in range(100):
            session_data = {
                "user_profile": {
                    "id": f"user_{i}",
                    "data": "x" * 1000,
                },  # Add some bulk
                "created_at": datetime.utcnow(),
                "expires_at": datetime.utcnow() + timedelta(hours=3),
            }
            cache_service.create_session(session_data)

        # Memory usage should increase
        final_usage = cache_service.get_memory_usage()
        assert final_usage > initial_usage

    def test_cache_cleanup_on_memory_pressure(self) -> None:
        """Should perform cleanup when memory pressure is detected."""
        from src.services.cache_service import CacheService

        cache_service = CacheService()

        # Simulate memory pressure
        with patch.object(cache_service, "_is_memory_pressure_high", return_value=True):
            with patch.object(
                cache_service, "cleanup_expired_sessions"
            ) as mock_cleanup_sessions:
                with patch.object(
                    cache_service, "clear_stale_tle_data"
                ) as mock_cleanup_tle:
                    cache_service.check_memory_pressure()

                    mock_cleanup_sessions.assert_called_once()
                    mock_cleanup_tle.assert_called_once()

    def test_lru_eviction_policy(self) -> None:
        """Should use LRU eviction policy for cache entries."""
        from src.services.cache_service import CacheService

        cache_service = CacheService()
        cache_service.max_session_size = 3

        # Create sessions
        session_ids = []
        for i in range(3):
            session_data = {
                "user_profile": {"id": f"user_{i}"},
                "created_at": datetime.utcnow(),
                "expires_at": datetime.utcnow() + timedelta(hours=3),
            }
            session_id = cache_service.create_session(session_data)
            session_ids.append(session_id)

        # Access first session to make it recently used
        cache_service.get_session(session_ids[0])

        # Add new session (should evict least recently used)
        new_session_data = {
            "user_profile": {"id": "user_new"},
            "created_at": datetime.utcnow(),
            "expires_at": datetime.utcnow() + timedelta(hours=3),
        }
        new_session_id = cache_service.create_session(new_session_data)

        # First session should still exist (was recently accessed)
        assert cache_service.get_session(session_ids[0]) is not None

        # Second session should be evicted (least recently used)
        assert cache_service.get_session(session_ids[1]) is None


class TestConcurrency:
    """Test concurrent access to cache."""

    def test_thread_safe_session_operations(self) -> None:
        """Should handle concurrent session operations safely."""
        from src.services.cache_service import CacheService
        import threading

        cache_service = CacheService()
        results = []

        def create_sessions(thread_id: int) -> None:
            for i in range(10):
                session_data = {
                    "user_profile": {"id": f"user_{thread_id}_{i}"},
                    "created_at": datetime.utcnow(),
                    "expires_at": datetime.utcnow() + timedelta(hours=3),
                }
                session_id = cache_service.create_session(session_data)
                results.append(session_id)

        # Create multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=create_sessions, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # All sessions should be created without conflicts
        assert len(results) == 50
        assert len(set(results)) == 50  # All unique session IDs

    def test_concurrent_cache_cleanup(self) -> None:
        """Should handle concurrent cache cleanup operations."""
        from src.services.cache_service import CacheService
        import threading

        cache_service = CacheService()

        # Add sessions
        for i in range(20):
            session_data = {
                "user_profile": {"id": f"user_{i}"},
                "created_at": datetime.utcnow(),
                "expires_at": datetime.utcnow() + timedelta(hours=3),
            }
            cache_service.create_session(session_data)

        def cleanup_worker() -> None:
            cache_service.cleanup_expired_sessions()

        # Run concurrent cleanup operations
        threads = []
        for _ in range(3):
            thread = threading.Thread(target=cleanup_worker)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Should complete without errors or deadlocks
        assert len(cache_service.session_cache) >= 0


class TestErrorHandling:
    """Test error handling in cache service."""

    def test_invalid_session_data_handling(self) -> None:
        """Should handle invalid session data gracefully."""
        from src.services.cache_service import CacheService

        cache_service = CacheService()

        invalid_session_data = [None, {}, {"invalid": "data"}, {"user_profile": None}]

        for invalid_data in invalid_session_data:
            with pytest.raises((ValueError, TypeError)) as exc_info:
                cache_service.create_session(invalid_data)

            assert (
                "session" in str(exc_info.value).lower()
                or "invalid" in str(exc_info.value).lower()
            )

    def test_cache_corruption_recovery(self) -> None:
        """Should recover from cache corruption gracefully."""
        from src.services.cache_service import CacheService

        cache_service = CacheService()

        # Simulate cache corruption
        cache_service.session_cache["corrupted"] = "invalid_data"

        # Should handle gracefully during operations
        try:
            cache_service.cleanup_expired_sessions()
            # Should complete without crashing
        except Exception as e:
            # Should raise appropriate error, not crash
            assert "corrupt" in str(e).lower() or "invalid" in str(e).lower()

    def test_memory_allocation_failure_handling(self) -> None:
        """Should handle memory allocation failures."""
        from src.services.cache_service import CacheService

        cache_service = CacheService()

        # Simulate memory allocation failure
        with patch("uuid.uuid4", side_effect=MemoryError("Out of memory")):
            with pytest.raises(MemoryError):
                session_data = {
                    "user_profile": {"id": "user_test"},
                    "created_at": datetime.utcnow(),
                    "expires_at": datetime.utcnow() + timedelta(hours=3),
                }
                cache_service.create_session(session_data)

"""Unit tests for FastAPI main application."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from src.main import app


@pytest.fixture
def client() -> TestClient:
    """TestClient fixture for FastAPI app."""
    return TestClient(app)


def test_health_check_endpoint(client: TestClient) -> None:
    """Test GET /health returns status healthy and a timestamp."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data


def test_cors_middleware(client: TestClient) -> None:
    """Test CORS headers are returned for OPTIONS requests."""
    response = client.options(
        "/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") is not None


@pytest.mark.asyncio
async def test_lifespan_events() -> None:
    """Test lifespan context manager triggers startup and shutdown functions."""
    with (
        patch("src.main.init_database") as mock_init_db,
        patch("src.main.init_scheduler") as mock_init_sch,
        patch("src.main.stop_scheduler") as mock_stop_sch,
    ):
        patch.object(mock_init_sch.return_value, "start").start()

        with TestClient(app):
            mock_init_db.assert_called_once()
            mock_init_sch.assert_called_once()

        mock_stop_sch.assert_called_once()

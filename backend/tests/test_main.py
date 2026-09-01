"""Tests for the anonymous FastAPI application."""

from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from src.main import app


def test_health_check_endpoint() -> None:
    """Return a healthy status and an ISO timestamp."""
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "healthy"
    assert "timestamp" in payload


def test_anonymous_cors_does_not_allow_credentials() -> None:
    """Allow the local frontend origin without credentialed CORS."""
    with TestClient(app) as client:
        response = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:4174",
                "Access-Control-Request-Method": "GET",
            },
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:4174"
    assert "access-control-allow-credentials" not in response.headers


def test_auth_routes_are_not_registered() -> None:
    """The public application has no OAuth or session endpoints."""
    paths = {route.path for route in app.routes}
    assert not any(path == "/auth" or path.startswith("/auth/") for path in paths)
    assert "/geography/country" in paths
    assert "/radio/stations/select" in paths


def test_lifespan_initializes_and_stops_scheduler() -> None:
    """Initialize the database and TLE-only scheduler around app usage."""
    scheduler = MagicMock()
    scheduler.running = False
    with (
        patch("src.main.init_database") as init_database,
        patch("src.main.init_scheduler", return_value=scheduler) as init_scheduler,
        patch("src.main.stop_scheduler") as stop_scheduler,
        TestClient(app),
    ):
        init_database.assert_called_once_with()
        init_scheduler.assert_called_once_with()
        scheduler.start.assert_called_once_with()

    stop_scheduler.assert_called_once_with()

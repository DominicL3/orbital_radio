"""Tests for anonymous radio station endpoints."""

from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from src.api.radio import get_radio_service
from src.main import app
from src.utils.exceptions import RadioBrowserError

STATION_UUID = "123e4567-e89b-12d3-a456-426614174000"


@pytest.fixture
def client() -> TestClient:
    """Create a FastAPI test client."""
    return TestClient(app)


@pytest.fixture(autouse=True)
def clear_dependency_overrides() -> None:
    """Prevent radio service overrides from leaking between tests."""
    yield
    app.dependency_overrides.pop(get_radio_service, None)


@pytest.fixture
def station() -> dict[str, object]:
    """Normalized station payload returned by the radio service."""
    return {
        "station_uuid": STATION_UUID,
        "name": "Example FM",
        "country_code": "JP",
        "tags": ["music", "jazz"],
        "favicon_url": "https://example.test/favicon.ico",
        "homepage_url": "https://example.test",
        "stream_url": "https://stream.example.test/live.mp3",
        "codec": "MP3",
        "bitrate": 128,
    }


def test_select_station_returns_normalized_station(
    client: TestClient, station: dict[str, object]
) -> None:
    """Select a station for a country and pass exclusions as a set."""
    service = Mock()
    service.select_station.return_value = station
    app.dependency_overrides[get_radio_service] = lambda: service

    response = client.post(
        "/radio/stations/select",
        json={
            "country_code": "jp",
            "exclude_station_uuids": [STATION_UUID],
        },
    )

    assert response.status_code == 200
    assert response.json() == station
    service.select_station.assert_called_once_with("JP", {STATION_UUID})


def test_select_station_returns_no_content_when_none_available(
    client: TestClient,
) -> None:
    """Return 204 when the service has no eligible country station."""
    service = Mock()
    service.select_station.return_value = None
    app.dependency_overrides[get_radio_service] = lambda: service

    response = client.post("/radio/stations/select", json={"country_code": "US"})

    assert response.status_code == 204
    assert response.content == b""


def test_select_station_maps_provider_outage_to_503(client: TestClient) -> None:
    """Hide upstream response details behind a safe service-unavailable error."""
    service = Mock()
    service.select_station.side_effect = RadioBrowserError("private upstream body")
    app.dependency_overrides[get_radio_service] = lambda: service

    response = client.post("/radio/stations/select", json={"country_code": "US"})

    assert response.status_code == 503
    assert (
        response.json()["detail"]
        == "Radio station directory is temporarily unavailable"
    )
    assert "private upstream body" not in response.text


def test_failed_station_reports_valid_uuid(client: TestClient) -> None:
    """Report a browser playback failure without creating server-side session state."""
    service = Mock()
    app.dependency_overrides[get_radio_service] = lambda: service

    response = client.post(f"/radio/stations/{STATION_UUID}/failed")

    assert response.status_code == 204
    service.report_failed_station.assert_called_once_with(STATION_UUID)


def test_failed_station_rejects_oversized_uuid(client: TestClient) -> None:
    """Reject oversized path values before touching the service."""
    service = Mock()
    app.dependency_overrides[get_radio_service] = lambda: service

    response = client.post(f"/radio/stations/{'x' * 129}/failed")

    assert response.status_code == 422
    service.report_failed_station.assert_not_called()


def test_select_station_validates_country_code(client: TestClient) -> None:
    """Reject non-ISO country inputs at the HTTP boundary."""
    service = Mock()
    app.dependency_overrides[get_radio_service] = lambda: service

    response = client.post("/radio/stations/select", json={"country_code": "Japan"})

    assert response.status_code == 422
    service.select_station.assert_not_called()

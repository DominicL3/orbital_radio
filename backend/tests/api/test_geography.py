"""Tests for the public offline geography endpoint."""

from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from src.api.geography import get_geographic_mapper
from src.main import app


@pytest.fixture
def client() -> TestClient:
    """Create a FastAPI test client."""
    return TestClient(app)


@pytest.fixture(autouse=True)
def clear_dependency_overrides() -> None:
    """Prevent mapper overrides from leaking between tests."""
    yield
    app.dependency_overrides.pop(get_geographic_mapper, None)


def test_returns_country_code_for_land(client: TestClient) -> None:
    """Return the mapper's ISO code for a land coordinate."""
    mapper = Mock()
    mapper.get_country_code.return_value = "JP"
    app.dependency_overrides[get_geographic_mapper] = lambda: mapper

    response = client.get("/geography/country?latitude=35.6762&longitude=139.6503")

    assert response.status_code == 200
    assert response.json() == {"country_code": "JP"}
    mapper.get_country_code.assert_called_once_with(35.6762, 139.6503)


def test_returns_null_for_ocean(client: TestClient) -> None:
    """Preserve an ocean lookup as a null country code."""
    mapper = Mock()
    mapper.get_country_code.return_value = None
    app.dependency_overrides[get_geographic_mapper] = lambda: mapper

    response = client.get("/geography/country?latitude=0&longitude=-140")

    assert response.status_code == 200
    assert response.json() == {"country_code": None}


@pytest.mark.parametrize(
    "query",
    [
        "latitude=91&longitude=0",
        "latitude=0&longitude=181",
        "latitude=nan&longitude=0",
        "latitude=0&longitude=inf",
    ],
)
def test_rejects_invalid_coordinates(client: TestClient, query: str) -> None:
    """Return validation errors before invoking the mapper."""
    response = client.get(f"/geography/country?{query}")

    assert response.status_code == 422

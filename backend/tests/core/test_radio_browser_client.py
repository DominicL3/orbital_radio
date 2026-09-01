"""Tests for the concrete Radio Browser integration."""

from unittest.mock import AsyncMock, Mock

import httpx
import pytest

STATION_UUID = "11111111-1111-4111-8111-111111111111"


def provider_station(**overrides: object) -> dict[str, object]:
    """Return a representative Radio Browser response object."""
    payload: dict[str, object] = {
        "stationuuid": STATION_UUID,
        "name": "Orbital FM",
        "countrycode": "JP",
        "tags": "Pop, Electronic",
        "favicon": "https://radio.example/favicon.png",
        "homepage": "https://radio.example/",
        "url": "https://radio.example/listen",
        "url_resolved": "https://radio.example/live.mp3",
        "codec": "MP3",
        "bitrate": 128,
        "hls": 0,
        "lastcheckok": 1,
        "clickcount": 100,
        "votes": 25,
    }
    payload.update(overrides)
    return payload


class FakeResponse:
    """Small response double compatible with the client."""

    def __init__(self, payload: object, status_code: int = 200) -> None:
        self.payload = payload
        self.status_code = status_code
        self.headers: dict[str, str] = {}

    def json(self) -> object:
        if isinstance(self.payload, Exception):
            raise self.payload
        return self.payload


@pytest.fixture
def client() -> object:
    from src.core.radio_browser_client import RadioBrowserClient

    instance = RadioBrowserClient(
        settings=Mock(
            radio_browser_user_agent="Orbital Radio tests/1.0",
            radio_request_timeout_seconds=2,
            radio_result_limit=25,
        )
    )
    instance._discover_mirrors = AsyncMock(  # type: ignore[attr-defined]
        return_value=["https://de1.api.radio-browser.info"]
    )
    return instance


@pytest.mark.asyncio
async def test_search_uses_countrycode_and_resolved_url(client: object) -> None:
    response = FakeResponse([provider_station()])
    client._http_client = Mock()  # type: ignore[attr-defined]
    client._http_client.get = AsyncMock(return_value=response)  # type: ignore[attr-defined]

    stations = await client.search_stations("jp", limit=10)  # type: ignore[attr-defined]

    assert len(stations) == 1
    assert stations[0].station_uuid == STATION_UUID
    assert stations[0].stream_url == "https://radio.example/live.mp3"
    call = client._http_client.get.call_args  # type: ignore[attr-defined]
    assert call.args[0].endswith("/json/stations/search")
    assert call.kwargs["params"] == {
        "countrycode": "JP",
        "hidebroken": "true",
        "is_https": "true",
        "limit": 10,
        "order": "clickcount",
        "reverse": "true",
    }
    assert "Orbital Radio tests/1.0" in call.kwargs["headers"]["User-Agent"]


@pytest.mark.asyncio
async def test_search_filters_non_music_broken_hls_and_unsupported_stations(
    client: object,
) -> None:
    response = FakeResponse(
        [
            provider_station(),
            provider_station(
                stationuuid="22222222-2222-4222-8222-222222222222", tags="news, pop"
            ),
            provider_station(stationuuid="33333333-3333-4333-8333-333333333333", hls=1),
            provider_station(
                stationuuid="44444444-4444-4444-8444-444444444444",
                codec="OGG",
            ),
            provider_station(
                stationuuid="55555555-5555-4555-8555-555555555555",
                url_resolved="http://radio.example/live.mp3",
            ),
            provider_station(
                stationuuid="66666666-6666-4666-8666-666666666666",
                lastcheckok=0,
            ),
        ]
    )
    client._http_client = Mock()  # type: ignore[attr-defined]
    client._http_client.get = AsyncMock(return_value=response)  # type: ignore[attr-defined]

    stations = await client.search_stations("JP", limit=25)  # type: ignore[attr-defined]

    assert [station.station_uuid for station in stations] == [STATION_UUID]


@pytest.mark.asyncio
async def test_search_fails_over_after_timeout_and_invalid_json(client: object) -> None:
    first = Mock()
    first.get = AsyncMock(side_effect=httpx.ReadTimeout("timed out"))
    second = Mock()
    second.get = AsyncMock(return_value=FakeResponse([provider_station()]))
    client._discover_mirrors = AsyncMock(  # type: ignore[attr-defined]
        return_value=[
            "https://de1.api.radio-browser.info",
            "https://fr1.api.radio-browser.info",
        ]
    )
    client._http_client = Mock()  # type: ignore[attr-defined]
    client._http_client.get = AsyncMock(  # type: ignore[attr-defined]
        side_effect=[httpx.ReadTimeout("timed out"), FakeResponse([provider_station()])]
    )

    stations = await client.search_stations("JP", limit=5)  # type: ignore[attr-defined]

    assert len(stations) == 1
    assert client._http_client.get.await_count == 2  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_search_fails_over_on_server_error(client: object) -> None:
    client._discover_mirrors = AsyncMock(  # type: ignore[attr-defined]
        return_value=[
            "https://de1.api.radio-browser.info",
            "https://fr1.api.radio-browser.info",
        ]
    )
    client._http_client = Mock()  # type: ignore[attr-defined]
    client._http_client.get = AsyncMock(  # type: ignore[attr-defined]
        side_effect=[FakeResponse({}, 503), FakeResponse([provider_station()])]
    )

    stations = await client.search_stations("JP", limit=5)  # type: ignore[attr-defined]

    assert len(stations) == 1
    assert client._http_client.get.await_count == 2  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_resolve_play_registers_click_and_normalizes_response(
    client: object,
) -> None:
    client._http_client = Mock()  # type: ignore[attr-defined]
    client._http_client.get = AsyncMock(return_value=FakeResponse(provider_station()))  # type: ignore[attr-defined]

    station = await client.resolve_play(STATION_UUID)  # type: ignore[attr-defined]

    assert station.station_uuid == STATION_UUID
    assert client._http_client.get.call_args.args[0].endswith(  # type: ignore[attr-defined]
        f"/json/url/{STATION_UUID}"
    )


@pytest.mark.asyncio
async def test_resolve_play_reuses_search_result_when_click_only_acknowledges(
    client: object,
) -> None:
    client._http_client = Mock()  # type: ignore[attr-defined]
    client._http_client.get = AsyncMock(  # type: ignore[attr-defined]
        side_effect=[FakeResponse([provider_station()]), FakeResponse({"ok": True})]
    )
    stations = await client.search_stations("JP", limit=5)  # type: ignore[attr-defined]

    resolved = await client.resolve_play(STATION_UUID)  # type: ignore[attr-defined]

    assert resolved == stations[0]


@pytest.mark.asyncio
async def test_discovery_falls_back_to_valid_servers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from src.core.radio_browser_client import RadioBrowserClient

    client = RadioBrowserClient(settings=Mock())
    monkeypatch.setattr(client, "_discover_dns_mirrors", Mock(return_value=[]))
    client._http_client = Mock()  # type: ignore[attr-defined]
    client._http_client.get = AsyncMock(  # type: ignore[attr-defined]
        return_value=FakeResponse(
            [
                {"url": "https://de1.api.radio-browser.info"},
                {"url": "http://unsafe.example"},
                {"url": "https://evil.example"},
            ]
        )
    )

    mirrors = await client._discover_mirrors()  # type: ignore[attr-defined]

    assert mirrors == ["https://de1.api.radio-browser.info"]

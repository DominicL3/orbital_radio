"""Tests for radio station filtering, caching, rotation, and failure handling."""

from unittest.mock import AsyncMock, Mock

import pytest


def station(
    uuid: str,
    *,
    bitrate: int | None = 128,
    codec: str = "MP3",
    country_code: str = "JP",
) -> object:
    from src.schemas.radio import RadioStation

    return RadioStation(
        station_uuid=uuid,
        name=f"Station {uuid[:4]}",
        country_code=country_code,
        tags=["pop"],
        favicon_url=None,
        homepage_url="https://radio.example/",
        stream_url=f"https://radio.example/{uuid}.mp3",
        codec=codec,
        bitrate=bitrate,
    )


FIRST = "11111111-1111-4111-8111-111111111111"
SECOND = "22222222-2222-4222-8222-222222222222"
THIRD = "33333333-3333-4333-8333-333333333333"


def service_with(client: object, clock: list[float]) -> object:
    from src.services.radio_service import RadioService

    return RadioService(
        client=client,
        settings=Mock(
            radio_cache_ttl_minutes=30,
            radio_failure_cache_minutes=10,
            radio_result_limit=25,
        ),
        clock=lambda: clock[0],
    )


@pytest.mark.asyncio
async def test_selects_station_and_registers_play(client: object = None) -> None:
    browser = Mock()
    browser.search_stations = AsyncMock(return_value=[station(FIRST), station(SECOND)])
    browser.resolve_play = AsyncMock(side_effect=lambda uuid: station(uuid))
    service = service_with(browser, [0.0])

    selected = await service.select_station("jp", set())  # type: ignore[attr-defined]

    assert selected.station_uuid == FIRST
    browser.search_stations.assert_awaited_once_with("JP", 25)
    browser.resolve_play.assert_awaited_once_with(FIRST)


@pytest.mark.asyncio
async def test_selects_station_with_unknown_bitrate() -> None:
    browser = Mock()
    browser.search_stations = AsyncMock(return_value=[station(FIRST, bitrate=None)])
    browser.resolve_play = AsyncMock(
        side_effect=lambda uuid: station(uuid, bitrate=None)
    )
    service = service_with(browser, [0.0])

    selected = await service.select_station("JP", set())  # type: ignore[attr-defined]

    assert selected.station_uuid == FIRST
    assert selected.bitrate is None


@pytest.mark.asyncio
async def test_uses_fresh_country_cache_and_rotates_strong_candidates() -> None:
    browser = Mock()
    browser.search_stations = AsyncMock(return_value=[station(FIRST), station(SECOND)])
    browser.resolve_play = AsyncMock(side_effect=lambda uuid: station(uuid))
    clock = [0.0]
    service = service_with(browser, clock)

    first = await service.select_station("JP", set())  # type: ignore[attr-defined]
    second = await service.select_station("JP", {FIRST})  # type: ignore[attr-defined]

    assert first.station_uuid == FIRST
    assert second.station_uuid == SECOND
    browser.search_stations.assert_awaited_once()


@pytest.mark.asyncio
async def test_excludes_failed_station_and_bounds_negative_cache() -> None:
    browser = Mock()
    browser.search_stations = AsyncMock(return_value=[station(FIRST), station(SECOND)])
    browser.resolve_play = AsyncMock(side_effect=lambda uuid: station(uuid))
    clock = [0.0]
    service = service_with(browser, clock)

    service.report_failed_station(FIRST)  # type: ignore[attr-defined]
    selected = await service.select_station("JP", set())  # type: ignore[attr-defined]

    assert selected.station_uuid == SECOND
    assert FIRST in service.failed_stations  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_expired_failure_entry_can_be_selected_again() -> None:
    browser = Mock()
    browser.search_stations = AsyncMock(return_value=[station(FIRST)])
    browser.resolve_play = AsyncMock(side_effect=lambda uuid: station(uuid))
    clock = [0.0]
    service = service_with(browser, clock)

    service.report_failed_station(FIRST)  # type: ignore[attr-defined]
    assert await service.select_station("JP", set()) is None  # type: ignore[attr-defined]

    clock[0] = 601.0
    selected = await service.select_station("JP", set())  # type: ignore[attr-defined]

    assert selected.station_uuid == FIRST


@pytest.mark.asyncio
async def test_returns_stale_cached_result_when_provider_is_unavailable() -> None:
    browser = Mock()
    browser.search_stations = AsyncMock(return_value=[station(FIRST)])
    browser.resolve_play = AsyncMock(side_effect=lambda uuid: station(uuid))
    clock = [0.0]
    service = service_with(browser, clock)

    await service.select_station("JP", set())  # type: ignore[attr-defined]
    clock[0] = 1801.0
    browser.search_stations.side_effect = RuntimeError("all mirrors unavailable")

    selected = await service.select_station("JP", set())  # type: ignore[attr-defined]

    assert selected.station_uuid == FIRST
    assert browser.search_stations.await_count == 2


@pytest.mark.asyncio
async def test_returns_none_for_no_eligible_station() -> None:
    browser = Mock()
    browser.search_stations = AsyncMock(return_value=[])
    service = service_with(browser, [0.0])

    assert await service.select_station("JP", set()) is None  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_click_registration_failure_does_not_discard_station() -> None:
    browser = Mock()
    browser.search_stations = AsyncMock(return_value=[station(FIRST)])
    browser.resolve_play = AsyncMock(side_effect=RuntimeError("click failed"))
    service = service_with(browser, [0.0])

    selected = await service.select_station("JP", set())  # type: ignore[attr-defined]

    assert selected.station_uuid == FIRST


@pytest.mark.asyncio
async def test_cache_is_bounded_to_64_countries() -> None:
    browser = Mock()
    browser.search_stations = AsyncMock(
        side_effect=lambda code, limit: [station(FIRST, country_code=code)]
    )
    browser.resolve_play = AsyncMock(
        side_effect=lambda uuid: station(uuid, country_code="JP")
    )
    service = service_with(browser, [0.0])

    for index in range(65):
        # The fake stations deliberately use JP metadata; service cache keys still
        # exercise the bounded country map without going through provider parsing.
        await service.select_station(
            f"{chr(65 + index // 26)}{chr(65 + index % 26)}", set()
        )  # type: ignore[attr-defined]

    assert len(service.country_cache) == 64  # type: ignore[attr-defined]

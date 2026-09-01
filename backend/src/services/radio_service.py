"""Station selection, in-memory caching, rotation, and failure handling."""

from __future__ import annotations

import inspect
import logging
import time
from collections import OrderedDict
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any

from src.config import get_settings
from src.core.radio_browser_client import is_music_station
from src.schemas.radio import RadioStation
from src.utils.exceptions import RadioBrowserError, RadioBrowserUnavailableError

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class _CountryCacheEntry:
    """A country result list and its monotonic insertion time."""

    stations: list[RadioStation]
    cached_at: float


class RadioService:
    """Coordinate the application's one Radio Browser provider."""

    COUNTRY_CACHE_LIMIT = 64
    FAILED_STATION_CACHE_LIMIT = 512

    def __init__(
        self,
        client: Any | None = None,
        settings: Any | None = None,
        clock: Callable[[], float] | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        if client is None:
            # Local import prevents a circular dependency during test injection.
            from src.core.radio_browser_client import RadioBrowserClient

            client = RadioBrowserClient(settings=self.settings)
        self.client = client
        self._clock = clock or time.monotonic
        self.cache_ttl_seconds = (
            self._setting_minutes(
                "radio_cache_ttl_minutes", 30, minimum=1, maximum=24 * 60
            )
            * 60
        )
        self.failure_ttl_seconds = (
            self._setting_minutes(
                "radio_failure_cache_minutes", 10, minimum=1, maximum=24 * 60
            )
            * 60
        )
        self.result_limit = self._setting_int(
            "radio_result_limit", 25, minimum=1, maximum=100
        )
        self._country_cache: OrderedDict[str, _CountryCacheEntry] = OrderedDict()
        self._failed_station_cache: OrderedDict[str, float] = OrderedDict()
        self._rotation_offsets: dict[str, int] = {}

    @property
    def country_cache(self) -> OrderedDict[str, _CountryCacheEntry]:
        """Expose the bounded country cache for diagnostics and tests."""
        return self._country_cache

    @property
    def failed_stations(self) -> set[str]:
        """Return currently negative-cached station UUIDs."""
        self._prune_failed_stations()
        return set(self._failed_station_cache)

    def _setting_int(
        self, name: str, default: int, *, minimum: int, maximum: int
    ) -> int:
        """Read a bounded integer from injected or process settings."""
        try:
            value = int(getattr(self.settings, name, default))
        except (TypeError, ValueError):
            value = default
        return min(max(value, minimum), maximum)

    def _setting_minutes(
        self, name: str, default: int, *, minimum: int, maximum: int
    ) -> int:
        """Read a bounded duration in minutes."""
        return self._setting_int(name, default, minimum=minimum, maximum=maximum)

    @staticmethod
    def _normalize_country_code(country_code: str) -> str:
        """Normalize the service country key."""
        if not isinstance(country_code, str):
            raise TypeError("country_code must be an ISO alpha-2 string")
        normalized = country_code.strip().upper()
        if len(normalized) != 2 or not normalized.isascii() or not normalized.isalpha():
            raise ValueError("country_code must be an ISO alpha-2 string")
        return normalized

    @staticmethod
    def _normalize_exclusions(values: Iterable[str] | None) -> set[str]:
        """Normalize UUID exclusions while ignoring blank optional values."""
        if values is None:
            return set()
        try:
            return {
                value.strip()
                for value in values
                if isinstance(value, str) and value.strip()
            }
        except TypeError as exc:
            raise ValueError("exclude_station_uuids must be iterable") from exc

    def _prune_failed_stations(self) -> None:
        """Remove expired negative-cache entries."""
        now = self._clock()
        expired = [
            station_uuid
            for station_uuid, expires_at in self._failed_station_cache.items()
            if expires_at <= now
        ]
        for station_uuid in expired:
            self._failed_station_cache.pop(station_uuid, None)

    async def _stations_for_country(self, country_code: str) -> list[RadioStation]:
        """Get fresh results or use a stale result list after provider failure."""
        now = self._clock()
        entry = self._country_cache.get(country_code)
        if entry is not None and now - entry.cached_at <= self.cache_ttl_seconds:
            self._country_cache.move_to_end(country_code)
            return list(entry.stations)

        try:
            stations = await self.client.search_stations(
                country_code, self.result_limit
            )
            if not isinstance(stations, list):
                raise RadioBrowserError("Radio Browser returned invalid stations")
            normalized = [
                station for station in stations if isinstance(station, RadioStation)
            ]
            self._country_cache[country_code] = _CountryCacheEntry(
                stations=normalized, cached_at=now
            )
            self._country_cache.move_to_end(country_code)
            while len(self._country_cache) > self.COUNTRY_CACHE_LIMIT:
                self._country_cache.popitem(last=False)
            return list(normalized)
        except Exception as exc:
            if entry is not None and entry.stations:
                # A stale list is still safer than switching to unrelated content.
                self._country_cache.move_to_end(country_code)
                logger.warning(
                    "Using stale radio station cache for %s after provider error: %s",
                    country_code,
                    exc,
                )
                return list(entry.stations)
            if isinstance(exc, RadioBrowserUnavailableError):
                raise
            raise RadioBrowserUnavailableError(
                f"Unable to load radio stations for {country_code}"
            ) from exc

    @staticmethod
    def _station_score(station: RadioStation) -> tuple[float, int, int]:
        """Rank healthy/popular provider results while favoring useful formats."""
        metrics = getattr(station, "_provider_metrics", {})
        provider_score = float(getattr(station, "_provider_score", 0.0) or 0.0)
        codec_score = 2 if station.codec in {"MP3", "AAC"} else 0
        bitrate_score = min(station.bitrate or 0, 320) / 320
        return (
            provider_score + codec_score + bitrate_score,
            int(metrics.get("clickcount", 0)),
            station.bitrate or 0,
        )

    def _eligible_stations(
        self,
        stations: Iterable[RadioStation],
        exclusions: set[str],
        country_code: str,
    ) -> list[RadioStation]:
        """Apply defense-in-depth filtering and current-page exclusions."""
        self._prune_failed_stations()
        unavailable = set(self._failed_station_cache)
        return [
            station
            for station in stations
            if isinstance(station, RadioStation)
            and station.country_code == country_code
            and station.station_uuid not in exclusions
            and station.station_uuid not in unavailable
            and is_music_station(station.tags)
        ]

    async def _register_play(self, station: RadioStation) -> RadioStation:
        """Best-effort click registration before handing a station to the API."""
        resolver = getattr(self.client, "resolve_play", None)
        if not callable(resolver):
            return station
        try:
            result = resolver(station.station_uuid)
            if inspect.isawaitable(result):
                result = await result
            if isinstance(result, RadioStation):
                if result.station_uuid != station.station_uuid:
                    raise RadioBrowserError("click response changed station UUID")
                return result
        except Exception as exc:  # noqa: BLE001 - click reporting is best effort
            logger.warning(
                "Could not register Radio Browser click for %s: %s",
                station.station_uuid,
                exc,
            )
        return station

    async def select_station(
        self,
        country_code: str,
        exclude_station_uuids: set[str],
    ) -> RadioStation | None:
        """Select and click-register a strong eligible station for a country."""
        code = self._normalize_country_code(country_code)
        exclusions = self._normalize_exclusions(exclude_station_uuids)
        stations = await self._stations_for_country(code)
        candidates = self._eligible_stations(stations, exclusions, code)
        if not candidates:
            return None
        ranked = sorted(
            candidates,
            key=lambda station: (
                -self._station_score(station)[0],
                -self._station_score(station)[1],
                -self._station_score(station)[2],
                station.station_uuid,
            ),
        )
        # Rotate through a small strong pool.  The first request is the best
        # result; subsequent requests do not pin a country to one broadcaster.
        pool = ranked[: min(5, len(ranked))]
        offset = self._rotation_offsets.get(code, 0) % len(pool)
        selected = pool[offset]
        self._rotation_offsets[code] = offset + 1
        return await self._register_play(selected)

    def report_failed_station(self, station_uuid: str) -> None:
        """Temporarily deprioritize a station that failed in the browser."""
        if not isinstance(station_uuid, str) or not station_uuid.strip():
            raise ValueError("station_uuid must be non-empty")
        self._prune_failed_stations()
        key = station_uuid.strip()
        self._failed_station_cache[key] = self._clock() + self.failure_ttl_seconds
        self._failed_station_cache.move_to_end(key)
        while len(self._failed_station_cache) > self.FAILED_STATION_CACHE_LIMIT:
            self._failed_station_cache.popitem(last=False)

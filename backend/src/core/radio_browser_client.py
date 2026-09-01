"""Concrete, defensive client for the Radio Browser REST API."""

from __future__ import annotations

import asyncio
import logging
import random
import socket
from collections import OrderedDict
from collections.abc import Iterable, Sequence
from typing import Any
from urllib.parse import quote, urlsplit, urlunsplit

import httpx

from src.config import get_settings
from src.schemas.radio import RadioStation
from src.utils.exceptions import (
    RadioBrowserError,
    RadioBrowserResponseError,
    RadioBrowserUnavailableError,
)

logger = logging.getLogger(__name__)

DEFAULT_DISCOVERY_HOST = "all.api.radio-browser.info"
DEFAULT_USER_AGENT = "Orbital Radio/1.0 (live radio; hobby project)"
MAX_RESULT_LIMIT = 100

# Tags are intentionally broad because Radio Browser tags are community supplied.
# The denylist is checked first so e.g. "news rock" remains non-music.
MUSIC_TAG_ALLOWLIST = frozenset(
    {
        "alternative",
        "ambient",
        "blues",
        "classical",
        "country",
        "dance",
        "disco",
        "electronic",
        "folk",
        "funk",
        "hip-hop",
        "hip hop",
        "house",
        "indie",
        "jazz",
        "latin",
        "metal",
        "music",
        "oldies",
        "pop",
        "r&b",
        "rap",
        "reggae",
        "rock",
        "soul",
        "ska",
        "techno",
        "top 40",
        "trance",
        "world",
    }
)
MUSIC_TAG_DENYLIST = frozenset(
    {
        "emergency",
        "education",
        "news",
        "podcast",
        "politics",
        "religious",
        "religion",
        "scanner",
        "sports",
        "talk",
        "weather",
    }
)


def _truthy_provider_flag(value: Any) -> bool:
    """Interpret Radio Browser's bool/int/string flags consistently."""
    if isinstance(value, str):
        return value.strip().casefold() in {"1", "true", "yes", "on"}
    return bool(value)


def _safe_number(value: Any) -> float:
    """Parse a non-negative provider ranking value."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    return number if number >= 0 else 0.0


def _safe_base_url(value: Any) -> str | None:
    """Accept only official HTTPS Radio Browser mirror URLs."""
    if not isinstance(value, str) or not value.strip():
        return None
    value = value.strip().rstrip("/")
    try:
        parsed = urlsplit(value)
    except ValueError:
        return None
    hostname = (parsed.hostname or "").lower().rstrip(".")
    if (
        parsed.scheme.lower() != "https"
        or not hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or not (
            hostname == "radio-browser.info" or hostname.endswith(".radio-browser.info")
        )
    ):
        return None
    if parsed.port not in (None, 443):
        return None
    # Preserve a configured API path only if it is a normal path; discovery
    # responses generally return a bare origin.
    return urlunsplit(("https", hostname, parsed.path.rstrip("/"), "", ""))


def _normalise_tag_values(value: Any) -> list[str]:
    """Normalize provider tags before applying the music policy."""
    if isinstance(value, str):
        values: Iterable[Any] = value.split(",")
    elif isinstance(value, (list, tuple, set)):
        values = value
    else:
        values = ()
    result: list[str] = []
    seen: set[str] = set()
    for item in values:
        if not isinstance(item, str):
            continue
        tag = item.strip()
        key = tag.casefold()
        if tag and key not in seen:
            seen.add(key)
            result.append(tag)
    return result


def is_music_station(tags: Sequence[str]) -> bool:
    """Return whether free-form tags suggest music, with denylist precedence."""
    normalized = [tag.strip().casefold() for tag in tags if isinstance(tag, str)]
    joined = ",".join(normalized)
    if any(term in joined for term in MUSIC_TAG_DENYLIST):
        return False
    return any(
        tag in MUSIC_TAG_ALLOWLIST
        or any(f" {term} " in f" {tag} " for term in MUSIC_TAG_ALLOWLIST)
        for tag in normalized
    )


class RadioBrowserClient:
    """Call Radio Browser mirrors and return only normalized playable stations."""

    def __init__(
        self,
        settings: Any | None = None,
        http_client: httpx.AsyncClient | None = None,
        mirrors: Sequence[str] | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.timeout = self._setting_float(
            "radio_request_timeout_seconds", 8.0, minimum=0.1, maximum=60.0
        )
        self.user_agent = str(
            getattr(self.settings, "radio_browser_user_agent", DEFAULT_USER_AGENT)
            or DEFAULT_USER_AGENT
        ).strip()
        self.default_result_limit = self._setting_int(
            "radio_result_limit", 25, minimum=1, maximum=MAX_RESULT_LIMIT
        )
        self._http_client = http_client
        self._configured_mirrors = tuple(
            mirror
            for mirror in (_safe_base_url(item) for item in (mirrors or ()))
            if mirror is not None
        )
        self._mirror_cache: list[str] | None = None
        self._station_cache: OrderedDict[str, RadioStation] = OrderedDict()
        self._station_cache_limit = 2048

    def _setting_int(
        self, name: str, default: int, *, minimum: int, maximum: int
    ) -> int:
        """Read a bounded integer setting without requiring a new config version."""
        try:
            value = int(getattr(self.settings, name, default))
        except (TypeError, ValueError):
            value = default
        return min(max(value, minimum), maximum)

    def _setting_float(
        self, name: str, default: float, *, minimum: float, maximum: float
    ) -> float:
        """Read a bounded float setting from the injected settings object."""
        try:
            value = float(getattr(self.settings, name, default))
        except (TypeError, ValueError):
            value = default
        return min(max(value, minimum), maximum)

    async def _get_http_client(self) -> tuple[httpx.AsyncClient, bool]:
        """Return an injected client or a short-lived configured HTTP client."""
        if self._http_client is not None:
            return self._http_client, False
        return (
            httpx.AsyncClient(
                timeout=self.timeout,
                headers={"User-Agent": self.user_agent, "Accept": "application/json"},
                follow_redirects=True,
            ),
            True,
        )

    async def _request_json(
        self,
        base_url: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
    ) -> Any:
        """Request JSON and convert transport/HTTP/JSON failures to safe errors."""
        client, should_close = await self._get_http_client()
        url = f"{base_url.rstrip('/')}/{path.lstrip('/')}"
        try:
            response = await client.get(
                url,
                params=params,
                headers={
                    "User-Agent": self.user_agent,
                    "Accept": "application/json",
                },
                timeout=self.timeout,
            )
            status_code = int(getattr(response, "status_code", 0))
            if status_code == 204:
                return None
            if status_code < 200 or status_code >= 300:
                raise RadioBrowserError(f"Radio Browser returned HTTP {status_code}")
            try:
                return response.json()
            except (ValueError, TypeError) as exc:
                raise RadioBrowserResponseError(
                    "Radio Browser returned invalid JSON"
                ) from exc
        except RadioBrowserError:
            raise
        except (httpx.TimeoutException, TimeoutError) as exc:
            raise RadioBrowserUnavailableError(
                "Radio Browser request timed out"
            ) from exc
        except httpx.RequestError as exc:
            raise RadioBrowserUnavailableError(
                "Radio Browser network request failed"
            ) from exc
        finally:
            if should_close:
                await client.aclose()

    @staticmethod
    def _discover_dns_mirrors() -> list[str]:
        """Discover official mirror hostnames through DNS and reverse DNS."""
        names: set[str] = set()
        try:
            records = socket.getaddrinfo(
                DEFAULT_DISCOVERY_HOST,
                443,
                type=socket.SOCK_STREAM,
            )
        except OSError:
            return []
        names.add(DEFAULT_DISCOVERY_HOST)
        addresses = {
            result[4][0]
            for result in records
            if len(result) > 4 and result[4] and result[4][0]
        }
        for address in addresses:
            try:
                reverse_name = socket.gethostbyaddr(address)[0]
            except (OSError, socket.herror):
                continue
            if reverse_name.lower().endswith(".radio-browser.info"):
                names.add(reverse_name)
        return [f"https://{name}" for name in names]

    async def _discover_mirrors(self) -> list[str]:
        """Return randomized mirrors, falling back to validated ``/json/servers``."""
        if self._configured_mirrors:
            mirrors = list(self._configured_mirrors)
            random.shuffle(mirrors)
            return mirrors
        if self._mirror_cache:
            mirrors = list(self._mirror_cache)
            random.shuffle(mirrors)
            return mirrors

        dns_mirrors = await asyncio.to_thread(self._discover_dns_mirrors)
        valid_dns = [
            mirror
            for mirror in (_safe_base_url(item) for item in dns_mirrors)
            if mirror is not None
        ]
        if valid_dns:
            self._mirror_cache = list(dict.fromkeys(valid_dns))
            mirrors = list(self._mirror_cache)
            random.shuffle(mirrors)
            return mirrors

        # DNS can be unavailable in a restricted deployment.  The discovery
        # endpoint is itself reached through the official all.api host and its
        # returned URLs are still validated before use.
        try:
            payload = await self._request_json(
                "https://" + DEFAULT_DISCOVERY_HOST, "/json/servers"
            )
        except RadioBrowserError:
            payload = []
        discovered: list[str] = []
        if isinstance(payload, list):
            for item in payload:
                if isinstance(item, dict):
                    mirror = _safe_base_url(item.get("url"))
                    if mirror is not None:
                        discovered.append(mirror)
        self._mirror_cache = list(dict.fromkeys(discovered))
        mirrors = list(self._mirror_cache)
        random.shuffle(mirrors)
        return mirrors

    @staticmethod
    def _validate_country_code(country_code: str) -> str:
        """Normalize and validate a country query."""
        if not isinstance(country_code, str):
            raise TypeError("country_code must be an ISO alpha-2 string")
        normalized = country_code.strip().upper()
        if len(normalized) != 2 or not normalized.isascii() or not normalized.isalpha():
            raise ValueError("country_code must be an ISO alpha-2 string")
        return normalized

    @staticmethod
    def _validate_limit(limit: int) -> int:
        """Validate the caller's result limit and bound it for the provider."""
        if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
            raise ValueError("limit must be a positive integer")
        return min(limit, MAX_RESULT_LIMIT)

    @classmethod
    def _normalize_station(
        cls, raw: Any, *, expected_country_code: str | None = None
    ) -> RadioStation | None:
        """Validate and normalize a single Radio Browser station object."""
        if not isinstance(raw, dict):
            return None
        station_uuid = raw.get("stationuuid")
        country_code = raw.get("countrycode")
        stream_url = raw.get("url_resolved")
        if not isinstance(station_uuid, str) or not station_uuid.strip():
            return None
        if not isinstance(country_code, str) or not country_code.strip():
            return None
        country_code = country_code.strip().upper()
        if expected_country_code is not None and country_code != expected_country_code:
            return None
        if not isinstance(stream_url, str) or not stream_url.strip():
            return None
        if _truthy_provider_flag(raw.get("hls")):
            return None
        if _truthy_provider_flag(raw.get("lastcheckok")) is False and (
            "lastcheckok" in raw and raw.get("lastcheckok") is not None
        ):
            return None
        if _truthy_provider_flag(raw.get("ssl_error")):
            return None
        tags = _normalise_tag_values(raw.get("tags"))
        if not is_music_station(tags):
            return None
        try:
            station = RadioStation(
                station_uuid=station_uuid,
                name=raw.get("name"),
                country_code=country_code,
                tags=tags,
                favicon_url=raw.get("favicon"),
                homepage_url=raw.get("homepage"),
                stream_url=stream_url,
                codec=raw.get("codec"),
                bitrate=cls._bitrate(raw.get("bitrate")),
                hls=False,
            )
        except (TypeError, ValueError):
            return None
        metrics = {
            "lastcheckok": 1.0,
            "clickcount": _safe_number(raw.get("clickcount")),
            "votes": _safe_number(raw.get("votes")),
            "clicktrend": _safe_number(raw.get("clicktrend")),
        }
        # Private metadata never appears in model_dump()/the API response but
        # gives RadioService enough information to rank healthy/popular stations.
        object.__setattr__(station, "_provider_metrics", metrics)
        object.__setattr__(
            station,
            "_provider_score",
            metrics["lastcheckok"] * 1000
            + metrics["clickcount"] * 0.1
            + metrics["votes"] * 2
            + metrics["clicktrend"] * 0.5,
        )
        return station

    @staticmethod
    def _bitrate(value: Any) -> int | None:
        """Normalize a possibly-null provider bitrate."""
        if value is None or value == "":
            return None
        try:
            bitrate = int(float(value))
        except (TypeError, ValueError):
            return None
        return max(0, min(bitrate, 100_000))

    def _remember(self, station: RadioStation) -> None:
        """Keep a bounded page-independent normalization cache for click ACKs."""
        self._station_cache[station.station_uuid] = station
        self._station_cache.move_to_end(station.station_uuid)
        while len(self._station_cache) > self._station_cache_limit:
            self._station_cache.popitem(last=False)

    async def search_stations(
        self, country_code: str, limit: int
    ) -> list[RadioStation]:
        """Search mirrors and return eligible normalized music stations."""
        code = self._validate_country_code(country_code)
        requested_limit = self._validate_limit(limit)
        mirrors = await self._discover_mirrors()
        if not mirrors:
            raise RadioBrowserUnavailableError("No Radio Browser mirrors discovered")
        params = {
            "countrycode": code,
            "hidebroken": "true",
            "is_https": "true",
            "limit": requested_limit,
            "order": "clickcount",
            "reverse": "true",
        }
        last_error: Exception | None = None
        for mirror in mirrors:
            try:
                payload = await self._request_json(
                    mirror, "/json/stations/search", params=params
                )
                if not isinstance(payload, list):
                    raise RadioBrowserResponseError(
                        "Radio Browser station search returned an invalid response"
                    )
                normalized: list[RadioStation] = []
                for raw in payload:
                    station = self._normalize_station(raw, expected_country_code=code)
                    if station is not None:
                        normalized.append(station)
                        self._remember(station)
                # A non-empty response made entirely of malformed entries is
                # treated as an invalid mirror response and triggers failover.
                if payload and not normalized:
                    raise RadioBrowserResponseError(
                        "Radio Browser returned no valid station records"
                    )
                return normalized
            except (RadioBrowserError, httpx.RequestError, ValueError) as exc:
                last_error = exc
                logger.warning("Radio Browser mirror failed (%s): %s", mirror, exc)
                continue
        raise RadioBrowserUnavailableError(
            "All Radio Browser mirrors failed"
        ) from last_error

    async def resolve_play(self, station_uuid: str) -> RadioStation:
        """Register a station click and return its normalized playable record."""
        if not isinstance(station_uuid, str) or not station_uuid.strip():
            raise ValueError("station_uuid must be non-empty")
        station_uuid = station_uuid.strip()
        mirrors = await self._discover_mirrors()
        if not mirrors:
            raise RadioBrowserUnavailableError("No Radio Browser mirrors discovered")
        path = f"/json/url/{quote(station_uuid, safe='')}"
        last_error: Exception | None = None
        cached = self._station_cache.get(station_uuid)
        for mirror in mirrors:
            try:
                payload = await self._request_json(mirror, path)
                candidate: RadioStation | None = None
                if isinstance(payload, dict):
                    expected = cached.country_code if cached is not None else None
                    candidate = self._normalize_station(
                        payload, expected_country_code=expected
                    )
                elif isinstance(payload, list) and payload:
                    expected = cached.country_code if cached is not None else None
                    candidate = self._normalize_station(
                        payload[0], expected_country_code=expected
                    )
                elif isinstance(payload, str) and cached is not None:
                    try:
                        candidate = cached.model_copy(update={"stream_url": payload})
                    except (TypeError, ValueError):
                        candidate = None
                # The click endpoint commonly acknowledges with {"ok": true}
                # rather than returning the station.  The prior normalized search
                # result is safe to return in that case.
                if candidate is None:
                    candidate = cached
                if candidate is None or candidate.station_uuid != station_uuid:
                    raise RadioBrowserResponseError(
                        "Radio Browser click response had no playable station"
                    )
                self._remember(candidate)
                return candidate
            except (RadioBrowserError, httpx.RequestError, ValueError) as exc:
                last_error = exc
                logger.warning(
                    "Radio Browser click mirror failed (%s): %s", mirror, exc
                )
                continue
        raise RadioBrowserUnavailableError(
            "All Radio Browser click mirrors failed"
        ) from last_error

    async def aclose(self) -> None:
        """Close an injected/persistent client when the application shuts down."""
        if self._http_client is not None:
            await self._http_client.aclose()

"""Normalized live-radio schemas exposed by the Orbital Radio API."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlsplit

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    PrivateAttr,
    field_validator,
    model_validator,
)

_COUNTRY_CODE = re.compile(r"^[A-Z]{2}$")
_HLS_SUFFIXES = (".m3u8", ".m3u8/", ".m3u8?")


def _is_hls_url(value: str) -> bool:
    """Return whether a URL identifies an HLS playlist."""
    path = urlsplit(value).path.lower()
    return path.endswith(_HLS_SUFFIXES) or ".m3u8" in path


def _validate_url(value: str, *, field_name: str, https_only: bool) -> str:
    """Validate a provider URL without ever dereferencing it."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a URL")
    value = value.strip()
    try:
        parsed = urlsplit(value)
    except ValueError as exc:
        raise ValueError(f"{field_name} must be a valid URL") from exc
    allowed_schemes = {"https"} if https_only else {"http", "https"}
    if parsed.scheme.lower() not in allowed_schemes:
        expected = "HTTPS" if https_only else "HTTP or HTTPS"
        raise ValueError(f"{field_name} must use {expected}")
    if not parsed.hostname or parsed.username or parsed.password:
        raise ValueError(f"{field_name} must include a safe hostname")
    return value


class RadioStation(BaseModel):
    """The small, stable station contract shared by backend and frontend.

    Radio Browser has a large and intentionally loose response object.  Only
    these normalized fields are serialized from the backend.  ``hls`` is kept
    solely as an internal validation marker and is excluded from API output.
    Provider ranking metrics are attached as private attributes by the client.
    """

    model_config = ConfigDict(
        extra="ignore",
        frozen=True,
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    station_uuid: str = Field(..., min_length=1, max_length=128)
    name: str = Field(..., min_length=1, max_length=512)
    country_code: str = Field(..., min_length=2, max_length=2)
    tags: list[str] = Field(default_factory=list)
    favicon_url: str | None = None
    homepage_url: str | None = None
    stream_url: str = Field(..., min_length=1, max_length=4096)
    codec: str = Field(..., min_length=1, max_length=32)
    bitrate: int | None = Field(default=None, ge=0, le=100_000)
    hls: bool = Field(default=False, exclude=True, repr=False)
    _provider_metrics: dict[str, float] = PrivateAttr(default_factory=dict)
    _provider_score: float = PrivateAttr(default=0.0)

    @field_validator("station_uuid", mode="before")
    @classmethod
    def normalize_station_uuid(cls, value: Any) -> str:
        """Require a non-empty opaque station identifier."""
        if not isinstance(value, str):
            value = str(value) if value is not None else ""
        value = value.strip()
        if not value:
            raise ValueError("station_uuid must be non-empty")
        return value

    @field_validator("name", mode="before")
    @classmethod
    def normalize_name(cls, value: Any) -> str:
        """Require a useful display name."""
        if not isinstance(value, str) or not value.strip():
            raise ValueError("name must be non-empty")
        return value.strip()

    @field_validator("country_code", mode="before")
    @classmethod
    def normalize_country_code(cls, value: Any) -> str:
        """Normalize an ISO alpha-2 country code to uppercase."""
        if not isinstance(value, str):
            raise TypeError("country_code must be an ISO alpha-2 code")
        value = value.strip().upper()
        if not _COUNTRY_CODE.fullmatch(value):
            raise ValueError("country_code must be an ISO alpha-2 code")
        return value

    @field_validator("tags", mode="before")
    @classmethod
    def normalize_tags(cls, value: Any) -> list[str]:
        """Accept provider comma-separated tags while returning clean strings."""
        if value is None:
            return []
        if isinstance(value, str):
            values: list[Any] = value.split(",")
        elif isinstance(value, (list, tuple, set)):
            values = list(value)
        else:
            raise TypeError("tags must be a list or comma-separated string")
        result: list[str] = []
        seen: set[str] = set()
        for item in values:
            if not isinstance(item, str):
                continue
            cleaned = item.strip()
            key = cleaned.casefold()
            if cleaned and key not in seen:
                seen.add(key)
                result.append(cleaned)
        return result

    @field_validator("favicon_url", "homepage_url", mode="before")
    @classmethod
    def normalize_optional_url(cls, value: Any, info: Any) -> str | None:
        """Keep optional provider links safe and never resolve them server-side."""
        if value is None or value == "":
            return None
        return _validate_url(value, field_name=info.field_name, https_only=False)

    @field_validator("stream_url", mode="before")
    @classmethod
    def normalize_stream_url(cls, value: Any) -> str:
        """Require a direct HTTPS stream URL."""
        result = _validate_url(value, field_name="stream_url", https_only=True)
        if _is_hls_url(result):
            raise ValueError("HLS streams are not supported")
        return result

    @field_validator("codec", mode="before")
    @classmethod
    def normalize_codec(cls, value: Any) -> str:
        """Normalize supported Radio Browser codec spellings."""
        if not isinstance(value, str) or not value.strip():
            raise ValueError("codec must be MP3 or AAC")
        normalized = value.strip().upper().replace("_", " ")
        if "HLS" in normalized or "MPEGURL" in normalized:
            raise ValueError("HLS streams are not supported")
        if "AAC" in normalized:
            return "AAC"
        if "MP3" in normalized or normalized in {
            "MPEG",
            "AUDIO/MPEG",
            "MPEG-1 LAYER 3",
        }:
            return "MP3"
        raise ValueError("codec must be MP3 or AAC")

    @model_validator(mode="after")
    def reject_hls(self) -> RadioStation:
        """Reject an explicit provider HLS marker as a second line of defense."""
        if self.hls or _is_hls_url(self.stream_url):
            raise ValueError("HLS streams are not supported")
        return self

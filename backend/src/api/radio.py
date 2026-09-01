"""Anonymous radio station selection endpoints."""

from __future__ import annotations

import inspect
from functools import lru_cache
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Path, Response, status
from pydantic import BaseModel, Field, field_validator

from src.schemas.radio import RadioStation
from src.utils.exceptions import NoEligibleStationError, RadioBrowserError

router = APIRouter(prefix="/radio", tags=["radio"])


def _is_valid_station_uuid(value: str) -> bool:
    """Require the station identifier format returned by Radio Browser."""
    try:
        UUID(value)
    except (AttributeError, TypeError, ValueError):
        return False
    return True


class StationSelectionRequest(BaseModel):
    """Input for selecting a station in the country beneath the satellite."""

    country_code: str = Field(min_length=2, max_length=2)
    exclude_station_uuids: list[str] = Field(default_factory=list, max_length=512)

    @field_validator("country_code")
    @classmethod
    def normalize_country_code(cls, value: str) -> str:
        """Normalize and validate an ISO alpha-2 country code."""
        normalized = value.strip().upper()
        if len(normalized) != 2 or not normalized.isalpha():
            raise ValueError("country_code must be a two-letter ISO code")
        return normalized

    @field_validator("exclude_station_uuids")
    @classmethod
    def validate_exclusions(cls, values: list[str]) -> list[str]:
        """Bound exclusion values before handing them to the in-memory service."""
        normalized: list[str] = []
        for value in values:
            candidate = value.strip()
            if not candidate or len(candidate) > 128 or not _is_valid_station_uuid(candidate):
                raise ValueError("exclude_station_uuids must contain valid station UUIDs")
            normalized.append(candidate)
        return normalized


@lru_cache(maxsize=1)
def get_radio_service() -> Any:
    """Return the process-wide radio service so its caches remain effective."""
    from src.services.radio_service import RadioService

    return RadioService()


def _is_radio_browser_error(error: BaseException) -> bool:
    """Recognize the shared provider exception across the integration boundary.

    Luna A owns the concrete client and service.  During a rolling deployment,
    an already-imported service may expose the same named exception from its
    client module; the class-name check keeps this thin HTTP adapter from
    leaking an upstream outage as a 500 while preserving unrelated errors.
    """
    return isinstance(error, RadioBrowserError) or error.__class__.__name__ == (
        "RadioBrowserError"
    )


@router.post(
    "/stations/select",
    response_model=RadioStation,
    status_code=status.HTTP_200_OK,
)
async def select_station(
    request: StationSelectionRequest = Body(...),  # noqa: B008
    service: Any = Depends(get_radio_service),  # noqa: B008
) -> Any:
    """Select and register one normalized eligible station for a country."""
    try:
        selected = service.select_station(
            request.country_code, set(request.exclude_station_uuids)
        )
        if inspect.isawaitable(selected):
            selected = await selected
    except NoEligibleStationError:
        selected = None
    except Exception as exc:
        if not _is_radio_browser_error(exc):
            raise
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Radio station directory is temporarily unavailable",
        ) from exc

    if selected is None:
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    return selected


@router.post("/stations/{station_uuid}/failed", status_code=status.HTTP_204_NO_CONTENT)
async def report_failed_station(
    station_uuid: str = Path(..., min_length=1, max_length=128),
    service: Any = Depends(get_radio_service),  # noqa: B008
) -> Response:
    """Temporarily deprioritize a station that failed in the browser."""
    if not _is_valid_station_uuid(station_uuid):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="station_uuid must be a valid UUID",
        )
    result = service.report_failed_station(station_uuid)
    if inspect.isawaitable(result):
        await result
    return Response(status_code=status.HTTP_204_NO_CONTENT)

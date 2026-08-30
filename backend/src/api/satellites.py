"""API router for satellite endpoints."""

from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, Query, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from src.config import utcnow
from src.schemas.satellite import (
    SatelliteListResponse,
    SatelliteResponse,
    TLEData,
)
from src.services.satellite_service import SatelliteService


def get_satellite_service() -> SatelliteService:
    """Dependency provider for SatelliteService instance.

    Returns:
        SatelliteService: Service instance.
    """
    from src.services.satellite_service import SatelliteService

    return SatelliteService()


def _parse_sat_key(satellite_id: str) -> int | str:
    """Parse satellite ID string into integer or string key.

    Args:
        satellite_id: Raw path parameter string.

    Returns:
        int | str: Parsed integer NORAD/database ID or string catalog key.
    """
    if satellite_id.isdigit():
        return int(satellite_id)
    return satellite_id


router = APIRouter(prefix="/satellites", tags=["satellites"])


@router.get("", response_model=SatelliteListResponse)
def list_satellites(
    category: str | None = Query(None),
    active_only: bool | None = Query(None),
    page: int | None = Query(None),
    page_size: int | None = Query(None),
    search: str | None = Query(None),
    include_freshness: bool | None = Query(None),
    service: SatelliteService = Depends(get_satellite_service),
) -> Any:
    """List satellites with optional filtering and pagination.

    Args:
        category: Filter by category string.
        active_only: Filter active satellites only.
        page: Page index.
        page_size: Page size limit.
        search: Substring search term for satellite name.
        include_freshness: Include data freshness metadata.
        service: Injected SatelliteService dependency.

    Returns:
        Any: JSON response containing satellites list or paginated payload.
    """
    if page is not None and page_size is not None:
        paginated = service.get_satellites_paginated(page, page_size)
        if include_freshness:
            paginated["data_freshness"] = service.get_data_freshness()
        return JSONResponse(
            status_code=status.HTTP_200_OK, content=jsonable_encoder(paginated)
        )

    if search:
        satellites = service.search_satellites_by_name(search)
    elif category:
        satellites = service.get_satellites_by_category(category)
    elif active_only:
        satellites = service.get_active_satellites()
    else:
        satellites = service.get_all_satellites()

    content: dict[str, Any] = {"satellites": satellites}
    if include_freshness:
        content["data_freshness"] = service.get_data_freshness()

    return JSONResponse(
        status_code=status.HTTP_200_OK, content=jsonable_encoder(content)
    )


@router.get("/{satellite_id}/tle", response_model=TLEData)
def get_satellite_tle(
    satellite_id: str,
    include_elements: bool | None = Query(False),
    service: SatelliteService = Depends(get_satellite_service),
) -> Any:
    """Get satellite TLE data.

    Args:
        satellite_id: Satellite identifier.
        include_elements: Include orbital elements flag.
        service: Injected SatelliteService dependency.

    Returns:
        Any: JSON response containing TLE data or error.
    """
    sat_key = _parse_sat_key(satellite_id)

    try:
        tle = service.get_satellite_tle(sat_key)
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": f"Failed to fetch TLE data: {e!s}"},
        )

    if tle is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": "TLE data not found"},
        )

    data = jsonable_encoder(tle)

    last_updated_str = data.get("last_updated")
    if last_updated_str:
        if isinstance(last_updated_str, str):
            try:
                dt = datetime.fromisoformat(last_updated_str)
            except Exception:
                dt = utcnow()
        else:
            dt = last_updated_str
        if utcnow() - dt > timedelta(hours=24):
            data["warning"] = "TLE data is stale"

    if include_elements and "orbital_elements" not in data:
        try:
            elements = service.get_satellite_orbital_elements(sat_key)
            data["orbital_elements"] = jsonable_encoder(elements)
        except Exception:
            pass

    return JSONResponse(status_code=status.HTTP_200_OK, content=jsonable_encoder(data))


@router.get("/{satellite_id}/positions")
def get_satellite_positions(
    satellite_id: str,
    duration_minutes: int = Query(90),
    service: SatelliteService = Depends(get_satellite_service),
) -> Any:
    """Get position predictions for satellite.

    Args:
        satellite_id: Satellite identifier.
        duration_minutes: Prediction duration in minutes.
        service: Injected SatelliteService dependency.

    Returns:
        Any: JSON response containing positions list or error payload.
    """
    if duration_minutes <= 0 or duration_minutes > 1440:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": "Invalid duration_minutes parameter"},
        )

    sat_key = _parse_sat_key(satellite_id)

    try:
        positions = service.get_satellite_positions(sat_key, duration_minutes)
    except ValueError as e:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"error": f"TLE data unavailable: {e!s}"},
        )
    except RuntimeError as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": f"Orbital calculation error: {e!s}"},
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": str(e)},
        )

    pos_list = []
    for pos in positions:
        pos_list.append(jsonable_encoder(pos))

    return JSONResponse(status_code=status.HTTP_200_OK, content={"positions": pos_list})


@router.get("/{satellite_id}/visibility")
def get_satellite_visibility(
    satellite_id: str,
    lat: float = Query(...),
    lon: float = Query(...),
    service: SatelliteService = Depends(get_satellite_service),
) -> Any:
    """Get satellite visibility windows for observer location.

    Args:
        satellite_id: Satellite identifier.
        lat: Observer latitude coordinate.
        lon: Observer longitude coordinate.
        service: Injected SatelliteService dependency.

    Returns:
        Any: JSON response containing visibility windows.
    """
    windows = service.get_visibility_windows(satellite_id, lat, lon)
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"visibility_windows": windows},
    )


@router.get("/{satellite_id}", response_model=SatelliteResponse)
def get_satellite_details(
    satellite_id: str,
    service: SatelliteService = Depends(get_satellite_service),
) -> Any:
    """Get satellite details by ID.

    Args:
        satellite_id: Satellite identifier.
        service: Injected SatelliteService dependency.

    Returns:
        Any: JSON response containing satellite details or error payload.
    """
    if not satellite_id or not satellite_id.strip():
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": "Invalid satellite ID format"},
        )

    sat_key = _parse_sat_key(satellite_id)

    if isinstance(sat_key, int) and (sat_key <= 0 or sat_key > 99999):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": "Invalid satellite ID range"},
        )

    try:
        sat = service.get_satellite_by_id(sat_key)
    except ValueError as e:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": f"Invalid satellite ID: {e!s}"},
        )

    if sat is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": "Satellite not found"},
        )

    return JSONResponse(status_code=status.HTTP_200_OK, content=jsonable_encoder(sat))

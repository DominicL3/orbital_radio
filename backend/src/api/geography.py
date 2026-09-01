"""Geographic lookup endpoints backed by offline country boundaries."""

import math
from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from src.core.geographic_mapper import GeographicMapper
from src.utils.exceptions import GeographicLookupError

router = APIRouter(prefix="/geography", tags=["geography"])


class CountryResponse(BaseModel):
    """Country code for a coordinate, or ``None`` over ocean/unknown areas."""

    country_code: str | None = None


@lru_cache(maxsize=1)
def get_geographic_mapper() -> GeographicMapper:
    """Return the process-wide mapper so GeoJSON is loaded only once."""
    return GeographicMapper()


@router.get("/country", response_model=CountryResponse)
def country_for_coordinates(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    mapper: GeographicMapper = Depends(get_geographic_mapper),  # noqa: B008
) -> CountryResponse:
    """Resolve WGS84 coordinates to an ISO 3166-1 alpha-2 code."""
    if not math.isfinite(latitude) or not math.isfinite(longitude):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Coordinates must be finite",
        )
    try:
        country_code = mapper.get_country_code(latitude, longitude)
    except (GeographicLookupError, OSError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Geographic lookup is unavailable",
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    return CountryResponse(country_code=country_code)

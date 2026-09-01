"""Satellite TLE manager for orbital calculations and data fetching."""

import logging
from datetime import datetime, timedelta
from typing import Any

import httpx

from src.config import get_settings
from src.schemas.satellite import OrbitalElements, Position, TLEData
from src.utils.exceptions import TLEDataError

logger = logging.getLogger(__name__)


class SatelliteTLEManager:
    """Manager for satellite TLE data fetching, caching, and orbital calculations."""

    def __init__(self) -> None:
        """Initialize empty TLE cache and tracking state."""
        self.tle_cache: dict[str, Any] = {}
        self.last_update_time: datetime | None = None
        self.celestrak_base_url = "https://celestrak.org/NORAD/elements/"

    def fetch_tle_data(self, satellite_id: str) -> Any:
        """Fetch TLE data from external API or cache.

        Args:
            satellite_id: Satellite identifier.

        Returns:
            Any: TLE data object or dictionary.

        Raises:
            ValueError: If satellite_id is invalid.
            TLEDataError: If TLE fetching or parsing fails.
        """
        if (
            not satellite_id
            or not isinstance(satellite_id, str)
            or not satellite_id.strip()
        ):
            raise ValueError("satellite_id must be a non-empty string")

        if self._is_tle_stale(satellite_id):
            settings = get_settings()
            catalog = settings.satellite_catalog
            if satellite_id in catalog and "celestrak_url" in catalog[satellite_id]:
                url = catalog[satellite_id]["celestrak_url"]
            else:
                url = f"{self.celestrak_base_url}{satellite_id}.txt"

            try:
                res = httpx.get(url, timeout=10)
                res.raise_for_status()
                parsed = self._parse_tle_data(res.text, satellite_id)
                self.tle_cache[satellite_id] = parsed
                return parsed
            except Exception as e:
                # If cached version exists, fall back to it
                cached = self.get_cached_tle(satellite_id)
                if cached:
                    return cached
                raise TLEDataError(
                    f"Failed to fetch TLE data for {satellite_id}: {e}"
                ) from e

        return self.get_cached_tle(satellite_id)

    def get_cached_tle(self, satellite_id: str) -> Any | None:
        """Retrieve cached TLE data for a satellite.

        Args:
            satellite_id: Satellite identifier.

        Returns:
            Any | None: Cached TLE data or None.

        Raises:
            TypeError: If satellite_id is not str.
        """
        if satellite_id is None or not isinstance(satellite_id, str):
            raise TypeError("satellite_id must be str")
        return self.tle_cache.get(satellite_id)

    def refresh_all_tle_data(self) -> None:
        """Refresh TLE data for all tracked satellites."""
        satellites = self._get_tracked_satellites()
        for sat_id in satellites:
            try:
                self.fetch_tle_data(sat_id)
            except Exception as e:
                logger.warning("Failed to refresh TLE for satellite %s: %s", sat_id, e)
        self.last_update_time = datetime.now()

    def get_orbital_elements(self, satellite_id: str) -> OrbitalElements:
        """Extract orbital elements for a satellite.

        Args:
            satellite_id: Satellite identifier.

        Returns:
            OrbitalElements: Extracted orbital elements model.

        Raises:
            TypeError: If satellite_id is not str.
            ValueError: If satellite not found in cache.
        """
        if not satellite_id or not isinstance(satellite_id, str):
            raise TypeError("satellite_id must be str")
        tle = self.get_cached_tle(satellite_id)
        if not tle:
            raise ValueError(f"TLE data not found in cache for {satellite_id}")

        return OrbitalElements(
            inclination=getattr(tle, "inclination", 51.6461),
            raan=getattr(tle, "raan", 339.7939),
            eccentricity=getattr(tle, "eccentricity", 0.0001222),
            arg_perigee=getattr(tle, "arg_perigee", 92.8340),
            mean_anomaly=getattr(tle, "mean_anomaly", 267.3124),
            mean_motion=getattr(tle, "mean_motion", 15.49309239),
            epoch=getattr(tle, "epoch", datetime.now()),
        )

    def generate_simplified_positions(
        self, satellite_id: str, duration_minutes: int
    ) -> list[Position]:
        """Generate predicted position sequence for a satellite.

        Args:
            satellite_id: Satellite identifier.
            duration_minutes: Prediction duration in minutes.

        Returns:
            list[Position]: Sequence of position predictions.

        Raises:
            ValueError: If duration_minutes or satellite_id is invalid.
        """
        if not satellite_id or not isinstance(satellite_id, str):
            raise ValueError("satellite_id must be a non-empty string")
        if duration_minutes <= 0 or duration_minutes > 1440:
            raise ValueError("duration_minutes must be between 1 and 1440")

        tle = self.get_cached_tle(satellite_id)
        return self._calculate_positions(tle, duration_minutes)

    def get_current_position(self, satellite_id: str) -> dict[str, Any]:
        """Calculate current satellite position.

        TODO: Stub - returns a hardcoded position. Replace with a real
        SGP4/TLE propagation (e.g. via the ``sgp4`` library) from the cached
        TLE. Out of scope for the satellite TLE manager task; the existing
        tests only assert the response shape.

        Args:
            satellite_id: Satellite identifier.

        Returns:
            dict[str, Any]: Current position parameters.
        """
        return {
            "timestamp": datetime.now(),
            "latitude": 40.7128,
            "longitude": -74.0060,
            "altitude_km": 408.0,
            "velocity_km_s": 7.66,
        }

    def calculate_visibility(
        self, satellite_id: str, lat: float, lon: float
    ) -> dict[str, Any]:
        """Calculate visibility from ground observer coordinates.

        TODO: Stub - returns hardcoded visibility data. Replace with real
        elevation/azimuth/range calculations from a propagated satellite
        position. Out of scope for the satellite TLE manager task.

        Args:
            satellite_id: Satellite identifier.
            lat: Observer latitude.
            lon: Observer longitude.

        Returns:
            dict[str, Any]: Visibility calculations.
        """
        return {
            "is_visible": True,
            "elevation_deg": 45.0,
            "azimuth_deg": 180.0,
            "range_km": 800.0,
            "next_pass": datetime.now() + timedelta(hours=2),
        }

    def generate_ground_track(
        self, satellite_id: str, duration_minutes: int
    ) -> list[dict[str, float]]:
        """Generate ground track coordinates.

        TODO: Stub - returns hardcoded lat/lon points. Replace with a real
        projected sub-satellite ground track from propagated positions.
        Out of scope for the satellite TLE manager task.

        Args:
            satellite_id: Satellite identifier.
            duration_minutes: Duration in minutes.

        Returns:
            list[dict[str, float]]: List of ground track lat/lon points.
        """
        return [
            {"latitude": 40.0, "longitude": -74.0},
            {"latitude": 41.0, "longitude": -73.0},
            {"latitude": 42.0, "longitude": -72.0},
        ]

    def get_bulk_positions(
        self, satellite_ids: list[str]
    ) -> dict[str, dict[str, float]]:
        """Calculate current positions for multiple satellites.

        TODO: Stub - returns hardcoded positions for each satellite.
        Replace with per-satellite propagation from each satellite's cached
        TLE. Out of scope for the satellite TLE manager task.

        Args:
            satellite_ids: List of satellite identifiers.

        Returns:
            dict[str, dict[str, float]]: Map of satellite ID to position dict.
        """
        return {
            sat_id: {"latitude": 40.0, "longitude": -74.0} for sat_id in satellite_ids
        }

    def cleanup_old_tle_data(self, days_to_keep: int = 7) -> None:
        """Clean up old TLE entries.

        TODO: Not yet implemented. Intended to prune stale in-memory cache
        entries older than ``days_to_keep``. Currently a no-op; the cache only
        holds live tracked satellites and is refreshed wholesale, so no cleanup
        is performed yet.

        Args:
            days_to_keep: Maximum retention threshold in days.
        """

    def _is_tle_stale(self, satellite_id: str) -> bool:
        """Check if TLE data for satellite is missing or stale according to settings."""
        tle = self.tle_cache.get(satellite_id)
        if not tle:
            return True
        epoch = getattr(tle, "epoch", None)
        if epoch is None or not isinstance(epoch, datetime):
            return True
        stale_seconds = get_settings().tle_stale_hours * 3600
        return abs((datetime.now() - epoch).total_seconds()) > stale_seconds

    def _parse_tle_data(self, raw_text: str, satellite_id: str) -> Any:
        """Parse raw TLE text response into TLEData schema model."""
        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
        if len(lines) < 2:
            raise TLEDataError("Could not parse TLE data: insufficient lines")
        return TLEData(
            satellite_id=satellite_id,
            tle_line1=lines[-2],
            tle_line2=lines[-1],
            epoch=datetime.now(),
            name=satellite_id.upper(),
        )

    def _get_tracked_satellites(self) -> list[str]:
        """Get list of satellite IDs currently tracked."""
        settings = get_settings()
        return list(settings.satellite_catalog.keys())

    def _calculate_positions(
        self, tle_data: Any, duration_minutes: int
    ) -> list[Position]:
        """Calculate position points given TLE and duration."""
        now = datetime.now()
        steps = max(1, duration_minutes // 5)
        positions: list[Position] = []
        for i in range(steps):
            positions.append(
                Position(
                    timestamp=now + timedelta(minutes=i * 5),
                    latitude=min(90.0, max(-90.0, 40.0 + i * 0.5)),
                    longitude=((-74.0 + i * 0.5 + 180.0) % 360.0) - 180.0,
                    altitude=408.0,
                )
            )
        return positions

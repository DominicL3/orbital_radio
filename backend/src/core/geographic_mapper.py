"""Offline latitude/longitude to ISO country-code resolution.

Country boundaries are repository-owned data and are loaded once when a
``GeographicMapper`` is constructed.  The mapper deliberately has no network
fallback and never chooses a nearest country for an ocean coordinate.
"""

from __future__ import annotations

import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any

from shapely.geometry import Point, shape
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union
from shapely.validation import make_valid

from src.config import PROJECT_ROOT, get_settings


class GeographicMapper:
    """Resolve coordinates against the bundled country boundary GeoJSON."""

    def __init__(self, boundaries_file: str | Path | None = None) -> None:
        """Load and retain country geometries in memory.

        Args:
            boundaries_file: Optional path to a GeoJSON file.  Relative paths
                are resolved from the backend project directory.

        Raises:
            FileNotFoundError: If the configured boundary file is unavailable.
            ValueError: If the boundary document is not a GeoJSON feature
                collection.
        """
        configured_path = boundaries_file or get_settings().country_boundaries_file
        self.boundaries_file = self._resolve_path(configured_path)
        self.country_boundaries: dict[str, BaseGeometry] = {}
        self._initialize_boundaries()

    @staticmethod
    def _resolve_path(boundaries_file: str | Path) -> Path:
        """Resolve a configured boundary path without changing process cwd."""
        path = Path(boundaries_file).expanduser()
        if not path.is_absolute():
            # The documented default is relative to ``backend/`` while
            # ``PROJECT_ROOT`` points at the repository root for .env loading.
            # Prefer the current directory when it already identifies a file,
            # then the backend package directory, then the repository root.
            if path.exists():
                return path.resolve()
            backend_path = Path(__file__).resolve().parents[2] / path
            if backend_path.exists():
                return backend_path.resolve()
            path = PROJECT_ROOT / path
        return path.resolve()

    def _initialize_boundaries(self) -> None:
        """Load country geometries once, merging multipart country features."""
        self.country_boundaries = self._load_boundary_data()

    def _load_boundary_data(self) -> dict[str, BaseGeometry]:
        """Read the configured GeoJSON and return ISO-code keyed geometries."""
        with self.boundaries_file.open(encoding="utf-8") as boundary_file:
            document = json.load(boundary_file)

        if document.get("type") != "FeatureCollection":
            raise ValueError("Country boundaries must be a GeoJSON FeatureCollection")

        geometries_by_code: defaultdict[str, list[BaseGeometry]] = defaultdict(list)
        for feature in document.get("features", []):
            if not isinstance(feature, dict):
                continue
            properties = feature.get("properties") or {}
            code = self._country_code(properties)
            geometry_data = feature.get("geometry")
            if code is None or not geometry_data:
                continue
            try:
                geometry = shape(geometry_data)
            except (TypeError, ValueError):
                continue
            if geometry.is_empty:
                continue
            if not geometry.is_valid:
                # Natural Earth contains a handful of valid-at-map-scale
                # polygons with ring defects (notably the United States).
                # Repair those local defects instead of silently turning a
                # populated country into ocean.
                geometry = make_valid(geometry)
            if not geometry.is_empty and geometry.is_valid:
                geometries_by_code[code].append(geometry)

        return {
            code: unary_union(geometries)
            for code, geometries in geometries_by_code.items()
        }

    @staticmethod
    def _country_code(properties: dict[str, Any]) -> str | None:
        """Choose a valid ISO alpha-2 property from a boundary feature."""
        # Some Natural Earth features have ``ISO_A2=-99`` while their
        # equivalent-country value is present in ``ISO_A2_EH``.
        for key in ("ISO_A2", "ISO_A2_EH"):
            value = properties.get(key)
            if not isinstance(value, str):
                continue
            code = value.strip().upper()
            if len(code) == 2 and code.isalpha():
                return code
        return None

    @staticmethod
    def _validate_coordinates(latitude: float, longitude: float) -> None:
        """Validate finite WGS84 coordinates."""
        if isinstance(latitude, bool) or isinstance(longitude, bool):
            raise TypeError("Coordinates must be numeric")
        try:
            latitude_value = float(latitude)
            longitude_value = float(longitude)
        except (TypeError, ValueError) as exc:
            raise ValueError("Coordinates must be numeric") from exc
        if not math.isfinite(latitude_value) or not math.isfinite(longitude_value):
            raise ValueError("Coordinates must be finite")
        if not -90.0 <= latitude_value <= 90.0:
            raise ValueError("Latitude must be between -90 and 90")
        if not -180.0 <= longitude_value <= 180.0:
            raise ValueError("Longitude must be between -180 and 180")

    def get_country_code(self, latitude: float, longitude: float) -> str | None:
        """Return the country containing a point, or ``None`` over water.

        ``covers`` includes boundary points, which avoids turning a sampled
        point exactly on a coastline into an ocean result.  It does not apply
        any nearest-country or maritime-zone fallback.
        """
        self._validate_coordinates(latitude, longitude)
        point = Point(float(longitude), float(latitude))
        for country_code, geometry in self.country_boundaries.items():
            if geometry.covers(point):
                return country_code
        return None

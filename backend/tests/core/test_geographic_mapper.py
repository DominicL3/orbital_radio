"""Tests for offline country resolution."""

import json
from pathlib import Path

import pytest

from src.core.geographic_mapper import GeographicMapper


@pytest.fixture
def boundaries_file() -> Path:
    """Return the repository-owned country boundary fixture."""
    return Path(__file__).parents[2] / "data" / "country_boundaries.geojson"


def test_loads_repository_boundaries(boundaries_file: Path) -> None:
    """Load country geometries once and expose ISO-code keys."""
    mapper = GeographicMapper(boundaries_file)

    assert mapper.country_boundaries
    assert {"US", "GB", "JP", "AU", "BR"}.issubset(mapper.country_boundaries)


@pytest.mark.parametrize(
    ("latitude", "longitude", "expected"),
    [
        (40.7128, -74.0060, "US"),
        (51.5074, -0.1278, "GB"),
        (35.6762, 139.6503, "JP"),
        (-33.8688, 151.2093, "AU"),
        (-23.5505, -46.6333, "BR"),
    ],
)
def test_resolves_land_coordinates(
    boundaries_file: Path, latitude: float, longitude: float, expected: str
) -> None:
    """Return uppercase ISO alpha-2 codes for representative land points."""
    mapper = GeographicMapper(boundaries_file)

    assert mapper.get_country_code(latitude, longitude) == expected


@pytest.mark.parametrize(
    ("latitude", "longitude"),
    [(25.0, -30.0), (0.0, -140.0), (-45.0, 90.0), (-60.0, 0.0)],
)
def test_returns_none_for_ocean_coordinates(
    boundaries_file: Path, latitude: float, longitude: float
) -> None:
    """Never substitute a nearest country for open water."""
    mapper = GeographicMapper(boundaries_file)

    assert mapper.get_country_code(latitude, longitude) is None


@pytest.mark.parametrize(
    ("latitude", "longitude"),
    [(91.0, 0.0), (-91.0, 0.0), (0.0, 181.0), (0.0, -181.0), (float("nan"), 0.0)],
)
def test_rejects_invalid_coordinates(
    boundaries_file: Path, latitude: float, longitude: float
) -> None:
    """Reject coordinates outside finite WGS84 ranges."""
    mapper = GeographicMapper(boundaries_file)

    with pytest.raises(ValueError):
        mapper.get_country_code(latitude, longitude)


def test_uses_iso_a2_eh_when_primary_code_is_unavailable(tmp_path: Path) -> None:
    """Use the equivalent-country ISO field for exceptional features."""
    document = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"ISO_A2": "-99", "ISO_A2_EH": "ZZ"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]],
                },
            }
        ],
    }
    path = tmp_path / "boundaries.geojson"
    path.write_text(json.dumps(document), encoding="utf-8")

    mapper = GeographicMapper(path)

    assert mapper.get_country_code(0.5, 0.5) == "ZZ"


def test_skips_invalid_features(tmp_path: Path) -> None:
    """Ignore malformed features while retaining usable boundary data."""
    document = {
        "type": "FeatureCollection",
        "features": [
            {"type": "Feature", "properties": {"ISO_A2": "US"}},
            {
                "type": "Feature",
                "properties": {"ISO_A2": "CA"},
                "geometry": {"type": "Polygon", "coordinates": []},
            },
        ],
    }
    path = tmp_path / "boundaries.geojson"
    path.write_text(json.dumps(document), encoding="utf-8")

    mapper = GeographicMapper(path)

    assert mapper.country_boundaries == {}

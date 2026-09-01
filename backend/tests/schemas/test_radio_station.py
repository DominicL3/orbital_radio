"""Tests for the normalized live-radio response schema."""

import pytest
from pydantic import ValidationError


def station_data(**overrides: object) -> dict[str, object]:
    """Return a representative normalized station payload."""
    payload: dict[str, object] = {
        "station_uuid": "11111111-1111-4111-8111-111111111111",
        "name": "Orbital FM",
        "country_code": "JP",
        "tags": ["Pop", "electronic"],
        "favicon_url": "https://radio.example/favicon.png",
        "homepage_url": "https://radio.example/",
        "stream_url": "https://radio.example/live.mp3",
        "codec": "MP3",
        "bitrate": 128,
    }
    payload.update(overrides)
    return payload


class TestRadioStation:
    """Validate the stable application station contract."""

    def test_accepts_normalized_station(self) -> None:
        from src.schemas.radio import RadioStation

        station = RadioStation(**station_data())

        assert station.station_uuid == "11111111-1111-4111-8111-111111111111"
        assert station.country_code == "JP"
        assert station.tags == ["Pop", "electronic"]
        assert station.codec == "MP3"
        assert station.model_dump() == station_data()

    def test_normalizes_country_and_codec(self) -> None:
        from src.schemas.radio import RadioStation

        station = RadioStation(**station_data(country_code="jp", codec="audio/aacp"))

        assert station.country_code == "JP"
        assert station.codec == "AAC"

    @pytest.mark.parametrize(
        "field,value",
        [
            ("station_uuid", ""),
            ("name", "   "),
            ("country_code", "USA"),
            ("country_code", "ZZZ"),
            ("stream_url", "http://radio.example/live.mp3"),
            ("stream_url", "https://radio.example/live.m3u8"),
            ("codec", "HLS"),
            ("codec", "OGG"),
            ("bitrate", -1),
        ],
    )
    def test_rejects_unsupported_or_invalid_values(
        self, field: str, value: object
    ) -> None:
        from src.schemas.radio import RadioStation

        with pytest.raises(ValidationError):
            RadioStation(**station_data(**{field: value}))

    def test_hls_is_internal_and_never_serialized(self) -> None:
        from src.schemas.radio import RadioStation

        station = RadioStation(**station_data(hls=False))

        assert station.hls is False
        assert "hls" not in station.model_dump()

    def test_optional_urls_and_tags_have_safe_defaults(self) -> None:
        from src.schemas.radio import RadioStation

        station = RadioStation(
            **station_data(tags=None, favicon_url=None, homepage_url=None)
        )

        assert station.tags == []
        assert station.favicon_url is None
        assert station.homepage_url is None

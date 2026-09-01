# Orbital Radio backend

The FastAPI backend is anonymous and stateless at the HTTP layer. It owns the
offline GeoJSON country lookup, Radio Browser metadata requests, station
eligibility/filtering, and bounded in-memory station cache. It does not own
accounts, OAuth, cookies, sessions, playlists, or station audio.

## Run locally

```sh
uv sync
uv run uvicorn src.main:app --reload --host 127.0.0.1 --port 8000
```

The default boundary file is `data/country_boundaries.geojson`. Override it
with `COUNTRY_BOUNDARIES_FILE` when running from another location. Configure
the frontend origin with `CORS_ORIGINS`; credentials are disabled because the
application has no browser authentication state.

## Radio behavior

`RadioBrowserClient` discovers and fails over between Radio Browser mirrors,
normalizes provider responses, and reports station clicks. `RadioService`
filters to healthy HTTPS, non-HLS MP3/AAC music stations and keeps country
results in a bounded TTL cache. Station metadata is never persisted and station
audio is never downloaded or relayed by this backend.

The public routes are:

```text
GET  /geography/country?latitude={lat}&longitude={lon}
POST /radio/stations/select
POST /radio/stations/{station_uuid}/failed
```

`/geography/country` returns `{"country_code": "JP"}` for land or
`{"country_code": null}` for ocean/unknown coordinates. Radio selection uses a
country code and an optional bounded exclusion list, returning `204` when no
eligible station exists and `503` for an unavailable station directory.

## Tests and lint

All external HTTP and DNS calls are mocked in automated tests:

```sh
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

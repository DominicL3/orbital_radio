# Orbital Radio Design Document

Orbital Radio lets users follow a simulated or real-time satellite in LEO with live radio provided by the [Radio Browser API](https://www.radio-browser.info/) from countries all around the world. As the selected satellite orbits the Earth, the application plays a music station from the country beneath it.

## System architecture

```text
+--------------------+     +---------------------+     +---------------------+
| Orbit position     | --> | Offline country     | --> | 3-second dwell      |
| (lat/lon)          |     | lookup (ISO/null)   |     | on country          |
+--------------------+     +---------------------+     +---------------------+
                                                               |
                                                               v
+--------------------+     +---------------------+     +---------------------+
| Radio Browser      | <-- | RadioBrowserClient  | <-- | Radio selection     |
| mirrors            |     |                     |     | service             |
+--------------------+     +---------------------+     +---------------------+
                                                               |
                                                    normalized RadioStation
                                                               |
                                                               v
+--------------------+     +---------------------+     +---------------------+
| Broadcaster HTTPS  | <-- | One HTMLAudioElement| <-- | Vue application     |
| MP3/AAC stream     |     |                     |     |                     |
+--------------------+     +---------------------+     +---------------------+
```

The backend owns country resolution, Radio Browser access, filtering, selection, and metadata caching. The frontend owns the current page's playback state, the wall-clock dwell timer, and the live audio element. The backend never proxies, relays, records, or modifies station audio; audio bytes travel directly from the broadcaster to the browser and never pass through FastAPI.

# Backend

## Core requirements

### Functional requirements

- Track or simulate the ISS position with an `OrbitPositionSource`-compatible frontend contract.
- Fetch and cache satellite TLE data for real position sources and future satellite expansion.
- Resolve latitude and longitude to an ISO 3166-1 alpha-2 country code using repository-owned offline boundary data.
- Return `null` for oceans and unresolved coordinates; do not substitute the nearest country.
- Query Radio Browser by `countrycode` and select an eligible music station.
- Filter out broken, non-HTTPS, HLS, and unsupported-codec stations.
- Keep country station results in a bounded in-memory TTL cache.
- Fail over between Radio Browser mirrors and between eligible stations.
- Report Radio Browser clicks through its `/json/url/{stationuuid}` behavior when a station is selected for playback.
- Expose only normalized application schemas, never raw Radio Browser responses.

### Non-functional requirements

- **Simplicity:** implement a concrete Radio Browser integration without speculative provider abstractions.
- **Maintainability:** separate external API parsing, station selection, geographic mapping, and HTTP routes.
- **Testability:** mock all external network traffic; automated tests must not depend on Radio Browser or live station availability.
- **Reliability:** use timeouts, mirror failover, stale cache fallback, and same-country station fallback.
- **Cost efficiency:** keep metadata traffic small and send audio directly from broadcasters to browsers.
- **Privacy:** collect no accounts, profiles, favorites, or persistent listener history.

## Technology stack

- **Backend:** FastAPI on Python 3.12+
- **HTTP client:** `httpx`
- **Satellite persistence:** SQLite
- **Station cache:** in-memory, bounded, TTL-based
- **Background tasks:** APScheduler for TLE refresh only
- **Geographic data:** offline GeoJSON country boundaries with Shapely/GeoPandas
- **Frontend:** Vue 3, Vite, TypeScript, and Cesium
- **Playback:** one browser `HTMLAudioElement`
- **Testing:** pytest, pytest-asyncio, Vitest, Vue Test Utils, and Playwright
- **Deployment:** Railway

## Core dependencies

```text
fastapi
uvicorn
httpx
apscheduler
python-dotenv
shapely
geopandas
pytest
pytest-asyncio
ruff
```

SQLite is provided by Python's standard library. No music SDK, OAuth library, HLS player, or audio-proxy dependency is required.

## Target directory structure

```text
orbital_radio/
├── CLAUDE.md
├── TODO_RADIO_CHANGES.md
├── backend/
│   ├── src/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── scheduler.py
│   │   ├── api/
│   │   │   ├── radio.py
│   │   │   └── satellites.py
│   │   ├── core/
│   │   │   ├── radio_browser_client.py
│   │   │   ├── geographic_mapper.py
│   │   │   └── satellite_tracker.py
│   │   ├── models/
│   │   │   └── satellite.py
│   │   ├── schemas/
│   │   │   ├── radio.py
│   │   │   └── satellite.py
│   │   ├── services/
│   │   │   ├── radio_service.py
│   │   │   └── satellite_service.py
│   │   └── utils/
│   ├── data/
│   │   └── country_boundaries.geojson
│   └── tests/
└── frontend/
    ├── src/
    │   ├── contracts/
    │   │   ├── radio.ts
    │   │   └── satellite.ts
    │   └── features/
    │       ├── globe/
    │       └── radio/
    │           ├── RadioPanel.vue
    │           └── radioState.ts
    └── e2e/
```

The structure is a target architecture. A service file should exist only when it contains real selection or caching behavior; do not create empty layers for symmetry.

## Satellite TLE manager

`core/satellite_tracker.py` fetches and caches TLE data and produces satellite positions.

```python
class SatelliteTLEManager:
    def fetch_tle_data(self, satellite_id: str) -> TLEData: ...
    def get_cached_tle(self, satellite_id: str) -> TLEData | None: ...
    def refresh_all_tle_data(self) -> None: ...
    def get_current_position(self, satellite_id: str) -> Position: ...
    def generate_positions(
        self,
        satellite_id: str,
        duration_minutes: int,
    ) -> list[Position]: ...
```

- Refresh TLE data every 12 hours through APScheduler.
- Support the ISS first and retain a catalog shape suitable for a few additional satellites.
- Calculations target smooth visualization rather than scientific or navigational accuracy.
- Keep the frontend demo source clearly labeled as a simulation until a real TLE-backed source replaces it.
- Do not return hard-coded country data from the completed implementation.

## Geographic mapper

`core/geographic_mapper.py` resolves sampled satellite coordinates with repository-owned offline boundaries.

```python
class GeographicMapper:
    def __init__(self, boundaries_file: str): ...
    def get_country_code(self, latitude: float, longitude: float) -> str | None: ...
```

- Load simplified country polygons once and retain them in memory.
- Return uppercase ISO 3166-1 alpha-2 codes such as `US`, `JP`, and `BR`.
- Return `None` for oceans, international waters, invalid points, and unresolved areas.
- Do not perform nearest-country substitution.
- Validate latitude and longitude at the API boundary.

## Radio Browser client

`core/radio_browser_client.py` is the only Radio Browser integration. It is concrete and provider-specific; do not introduce `StationDirectory`, provider adapters, or a generic provider interface.

```python
class RadioBrowserClient:
    async def search_stations(
        self,
        country_code: str,
        limit: int,
    ) -> list[RadioStation]: ...

    async def resolve_play(self, station_uuid: str) -> RadioStation: ...
```

Implementation requirements:

- Discover API mirrors through `all.api.radio-browser.info` or the `_api._tcp.radio-browser.info` SRV record.
- Randomize the discovered mirrors and retry the next mirror after timeouts, connection failures, retryable server errors, or invalid JSON.
- Never hard-code one Radio Browser server.
- Send a descriptive application `User-Agent`.
- Use `stationuuid`, not the legacy `id` field.
- Use uppercase `countrycode`, not the deprecated country-name field.
- Query `/json/stations/search` with `hidebroken=true`, `is_https=true`, a bounded `limit`, and explicit ordering.
- Normalize `url_resolved`, which resolves redirects and M3U/PLS/ASX playlists for browser clients.
- Apply strict response validation before data reaches the service or API layer.
- Never fetch arbitrary client-supplied URLs and never fetch station audio.

## Radio selection service

`services/radio_service.py` owns provider-specific filtering, result caching, rotation, and failure handling.

```python
class RadioService:
    async def select_station(
        self,
        country_code: str,
        exclude_station_uuids: set[str],
    ) -> RadioStation | None: ...

    def report_failed_station(self, station_uuid: str) -> None: ...
```

This service is not a provider abstraction. It directly coordinates `RadioBrowserClient` for the application's one provider.

## Country and station switching

Radio changes follow the country beneath the satellite. A new land country must remain unchanged for three continuous wall-clock seconds before the radio changes, and simulation speed does not alter this dwell time. Ocean or unresolved positions cancel a pending change and keep the current station playing.

```text
+------------------------+
| Sample satellite       |
| latitude/longitude     |
+------------------------+
            |
            v
+------------------------+       ocean / unknown
| Resolve ISO country    | ------------------------------+
+------------------------+                               |
            | land country                               |
            v                                            |
+------------------------+       yes                     |
| Already the committed  | ------------------------------+
| radio country?         |                               |
+------------------------+                               |
            | no                                         |
            v                                            |
+------------------------+       changed before 3 sec    |
| Same new country for   | ------------------------------+
| 3 wall-clock seconds?  |                               |
+------------------------+                               |
            | yes                                        |
            v                                            v
+------------------------+       none available   +------------------------+
| Select eligible HTTPS  | ---------------------->| Keep current station   |
| MP3/AAC music station  |                        | (or wait if none yet)  |
+------------------------+                        +------------------------+
            |
            | station selected
            v
+------------------------+       error / stall
| Play live in the one   | ------------------------------+
| HTMLAudioElement       |                               |
+------------------------+                               |
            ^                                            |
            |                                            |
            +---- select another eligible UUID <---------+
                  from the same committed country
```

The dwell controller uses real elapsed time. If the simulated orbit moves through a country in less than three wall-clock seconds, that country does not trigger a station change. If an eligible station cannot be found, keep the current working station; if no station has played yet, remain in the waiting state.

### Radio station eligibility

A station is eligible only when it represents music on a best-effort basis and all of the following are true:

- `lastcheckok` is true.
- `url_resolved` uses HTTPS.
- `hls` is false.
- The normalized codec is MP3 or AAC.
- The station contains at least one approved music tag.
- The station contains no explicit non-music denylist tag.
- The UUID and resolved stream URL are present and valid.

The music allowlist should include broad tags such as `music`, `rock`, `pop`, `jazz`, `classical`, `electronic`, `dance`, `folk`, `country`, `hip-hop`, `reggae`, `metal`, `blues`, `soul`, `funk`, and `world music`. The denylist should include tags such as `news`, `talk`, `sports`, `religious`, `politics`, `weather`, `scanner`, `emergency`, `education`, and `podcast`.

Radio Browser tags are free-form community metadata. Music-only behavior is therefore best-effort, and the UI must not claim editorial certification.

### Ranking and rotation

- Prefer recently healthy stations and MP3 where otherwise equivalent.
- Reject nonsensical or unusable bitrates; bitrate is a quality signal, not an absolute guarantee.
- Use Radio Browser vote/click signals to form a strong candidate pool.
- Rotate or randomize within that pool so every visit does not deterministically receive the same station.
- Exclude the current station on manual Next and exclude stations that failed during the current page visit.
- Keep a short, bounded process-wide negative cache for reported failures.
- If no candidate remains, return `None`; never fall back to non-music, HTTP, HLS, another country, or a commercial provider.

## Station caching

- Cache normalized eligible station lists by country code in memory.
- Use a configurable TTL, with 30 minutes as the default.
- Bound the number of cached countries and stations.
- Serve still-usable stale data when every Radio Browser mirror is temporarily unavailable.
- Do not persist station metadata to SQLite.
- Do not prefetch every country and do not add a station-refresh scheduler job.
- Negative-cache a locally failed station for a short configurable period, with 10 minutes as the default.

## Data models and schemas

### Satellite model

SQLite persists satellite catalog and TLE information only.

```python
class Satellite:
    id: int
    name: str
    norad_id: int
    category: str
    tle_line1: str | None
    tle_line2: str | None
    tle_epoch: datetime | None
    is_active: bool
    last_updated: datetime | None
```

### Radio station schema

`RadioStation` is a non-persistent Pydantic response schema, not a database model and not a provider-neutral domain abstraction.

```python
class RadioStation(BaseModel):
    station_uuid: str
    name: str
    country_code: str
    tags: list[str]
    favicon_url: str | None
    homepage_url: str | None
    stream_url: str
    codec: Literal["MP3", "AAC"]
    bitrate: int | None
```

The matching TypeScript contract uses the same meaning and stable field names. Raw Radio Browser fields must not leak into frontend feature code.

There is no user, session, favorite, playlist, track, played-item, playback-position, or cached-station database model.

## API design

### Geographic endpoint

```text
GET /geography/country?latitude={lat}&longitude={lon}
```

Returns a small response containing `country_code: string | null`. The frontend may sample this endpoint at a modest fixed interval; it must not call it on every animation frame.

### Radio endpoints

```text
POST /radio/stations/select
POST /radio/stations/{station_uuid}/failed
```

The selection request contains:

```json
{
  "country_code": "JP",
  "exclude_station_uuids": []
}
```

`POST /radio/stations/select` selects one eligible station, registers the Radio Browser play/click resolution, and returns `RadioStation`. It returns a clear no-station response when no eligible candidate exists.

The failure endpoint accepts a Radio Browser station UUID, places it in the bounded negative cache, and contains no arbitrary URL parameter. It is advisory and must be rate-limited or otherwise protected from unbounded cache growth.

### Satellite endpoints

```text
GET /satellites
GET /satellites/{id}
GET /satellites/{id}/tle
GET /satellites/{id}/positions
```

### Health endpoints

```text
GET /health
GET /status/satellites
```

Health responses may report cache counts and last TLE refresh time but must not expose station stream URLs beyond normal selection responses.

## Background tasks

APScheduler exists only for satellite maintenance.

```python
@scheduler.scheduled_job("interval", hours=12)
async def refresh_tle_data() -> None:
    await satellite_service.refresh_all_tle_data()
```

There are no authentication cleanup, user-session cleanup, playlist refresh, station prefetch, or played-history jobs.

## Error handling

Use explicit application exceptions that preserve safe, user-facing behavior without exposing upstream response bodies.

```python
class TLEDataError(Exception): ...
class GeographicLookupError(Exception): ...
class RadioBrowserError(Exception): ...
class NoEligibleStationError(Exception): ...
```

- Timeouts and temporary mirror failures trigger mirror failover.
- Invalid upstream data is rejected and logged without returning it to the browser.
- Exhausted mirrors may use still-usable stale country cache entries.
- Exhausted station candidates produce a no-station result; they do not broaden content or transport rules.
- Browser playback failures trigger another same-country selection and a bounded failure report.

## Configuration

```dotenv
# Application
ENVIRONMENT=development
LOG_LEVEL=INFO
CORS_ORIGINS=http://localhost:3000,http://localhost:8000

# Database and geographic data
DATABASE_PATH=./orbital_radio.db
COUNTRY_BOUNDARIES_FILE=./data/country_boundaries.geojson

# Satellite data
TLE_REFRESH_HOURS=12
TLE_STALE_HOURS=12

# Radio Browser metadata requests
RADIO_BROWSER_USER_AGENT=OrbitalRadio/0.1
RADIO_REQUEST_TIMEOUT_SECONDS=5
RADIO_RESULT_LIMIT=50
RADIO_CACHE_TTL_MINUTES=30
RADIO_FAILURE_CACHE_MINUTES=10

# Frontend radio behavior
VITE_COUNTRY_DWELL_SECONDS=3
```

The dwell value is three wall-clock seconds. Radio Browser requires no API key. The application has no secret key, OAuth settings, cookie settings, or user-session configuration.

# Frontend

Frontend-specific ownership and coding boundaries remain in `frontend/AGENTS.md`. The rules below define the radio behavior shared with the backend.

## Radio state

The frontend is anonymous: it has no accounts, login, favorites, preferences, or persistent listening history. It keeps only page-lifetime state:

```typescript
interface RadioStation {
  stationUuid: string
  name: string
  countryCode: string
  tags: string[]
  faviconUrl: string | null
  homepageUrl: string | null
  streamUrl: string
  codec: 'MP3' | 'AAC'
  bitrate: number | null
}

type RadioStatus =
  | 'waiting'
  | 'connecting'
  | 'playing'
  | 'paused'
  | 'retrying'
  | 'unavailable'
```

The player owns:

- One long-lived `HTMLAudioElement`
- The current normalized station
- The current committed country
- The pending country and wall-clock timer
- A bounded in-memory set of failed or recently used UUIDs for the page visit
- Playback and connection status

It does not use local storage, cookies, IndexedDB, or browser account state.

## Player behavior

- The first Play action is a user gesture and requests a station for the current committed land country.
- Assign HTTPS MP3/AAC streams directly to the audio element without HLS or Web Audio processing.
- Do not set `crossorigin` unless a concrete browser requirement justifies it; basic cross-origin media playback does not require reading the audio response.
- Pause stops or pauses the live connection. Resume reconnects to the station's current live point rather than an old timestamp.
- Next requests another eligible station for the committed country while excluding the current UUID.
- Automatic country switching begins only after initial user-initiated playback.
- On `error` or sustained `stalled`, report the failed UUID and request another station in the same committed country.
- A country-resolution request runs at a modest cadence independent of Cesium's animation frames.
- Ocean/unknown results cancel pending dwell timers but do not clear the committed radio country or current station.

## Radio panel presentation

Display:

- Station name
- Country code or country label
- Station favicon with a safe visual fallback
- A compact selection of tags
- Live/connecting/paused/retrying/unavailable state
- Play/Pause and Next controls

Now-playing song and program metadata is out of scope. Do not display fake artist names, fake tracks, duration, seek position, animated progress pretending to represent a finite song, favorites, or personalization.

# Testing strategy

## Backend tests

- Mock DNS discovery and every `httpx` request.
- Test mirror randomization/failover, timeouts, retryable errors, malformed JSON, and exhausted mirrors.
- Test `stationuuid`, `countrycode`, `url_resolved`, click resolution, and descriptive User-Agent behavior.
- Test HTTPS-only, non-HLS, MP3/AAC, broken-station, allowlist, and denylist filtering.
- Test cache TTL, stale fallback, bounded negative cache, and exclusion of failed/current UUIDs.
- Test ocean country resolution and representative land boundary points using offline fixtures.
- Test no-station behavior without broadening the content, country, codec, or HTTPS rules.
- Use FastAPI test clients for geographic, radio, satellite, health, validation, and CORS routes.
- Automated tests must never require public DNS, Radio Browser availability, or a live broadcaster stream.

## Frontend tests

- Use fake timers to verify exactly three wall-clock seconds are required for a stable new country.
- Verify the timer resets when a candidate country changes and cancels on ocean/unknown.
- Verify simulation speed does not change dwell duration.
- Verify initial audible playback requires a user action.
- Verify automatic switching is inactive before that action.
- Verify one audio element is reused when stations change.
- Verify Pause/Play, Next, rejected `play()` promises, `error`, `stalled`, retry, and unavailable states.
- Mock backend responses; Vitest and Playwright must not open live station streams.

## Coverage and quality

- Maintain meaningful unit coverage for selection, filtering, failover, dwell timing, and fallback behavior.
- Prefer behavioral tests over tests that merely assert implementation details.
- Use in-memory SQLite for satellite persistence tests.
- Keep external data fixtures small and representative.

# Deployment

- Deploy the FastAPI backend and Vue frontend on Railway or equivalent HTTPS origins.
- Configure explicit frontend origins in `CORS_ORIGINS`.
- Credentialed CORS is unnecessary because the application has no cookies or authorization headers.
- The backend service needs ordinary outbound HTTPS/DNS access for Radio Browser metadata and TLE data.
- Station audio bandwidth goes from the broadcaster to the browser, not through Railway.
- The `/health` endpoint is the deployment health-check target.

# Documentation and development rules

## Python documentation and typing

- Use Google-style docstrings for Python modules, classes, and public functions.
- Use Python 3.12+ type hints and `| None` for optionals.
- Avoid `typing.Any` except at untrusted external-data boundaries, and normalize those values before returning application schemas.
- Keep provider field names confined to the Radio Browser client and normalization code.

## Development setup

```bash
cd backend
uv sync
uv run uvicorn src.main:app --reload
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

For frontend work:

```bash
cd frontend
npm ci
npm run test
npm run build
```

Use the exact scripts defined in `frontend/package.json`; run Playwright when changes affect end-to-end radio or globe behavior.

## Required backend code-quality check

After every backend code change, run both commands from `backend/` before considering the work complete:

```bash
uv run ruff check .
uv run ruff format --check .
```

Resolve Ruff findings in code rather than suppressing them unless a suppression is necessary and explained.

## README expectations

Repository documentation must explain:

- The satellite-to-country-to-radio concept
- Anonymous live-radio behavior and the three-second dwell rule
- Radio Browser's role and the best-effort nature of community metadata
- HTTPS MP3/AAC playback constraints
- Backend and frontend setup
- Environment variables
- Test and quality commands
- The fact that the application links directly to broadcaster streams and does not relay or record audio

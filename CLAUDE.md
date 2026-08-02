# Orbital Radio Design Document

The Orbital Radio is a web-based music streaming application that combines real-time satellite trajectories with geographic-based Spotify playlists. As satellites orbit Earth, the application dynamically selects and plays popular music from each country/region the satellite passes over.

# Backend
## Core Requirements

### Functional Requirements
- **Spotify Integration**: Authenticate users via Spotify OAuth and access music playback controls
- **Satellite Tracking**: Approximate the real-time position of the International Space Station (ISS) for MVP, with architecture designed to support additional satellites in future iterations
- **Geographic Music Mapping**: Generate playlists using popular music from each country/region with offline country boundary detection
- **TLE Data Management**: Fetch and cache satellite orbital data for client-side calculations
- **Playlist Pre-Caching**: Pre-fetch and cache Spotify playlists to avoid rate limiting during active playback
- **Playlist Intelligence**: Generate playlists for orbital segments with smooth playback transitions
- **Song Duration Filtering**: Only include tracks between 1-8 minutes in duration
- **Session Management**: Manage temporary user sessions without persistent storage
- **Track Deduplication**: Prevent song repetition within orbital sessions using cached played-song sets
- **Country Cooldown**: Implement configurable cooldown period (default: 5 songs) to prevent oversampling large countries like USA and Russia

### Non-Functional Requirements
- **Simplicity**: Prioritize minimal complexity and fast development iteration
- **Maintainability**: Clear code structure with separation of concerns
- **Testability**: Unit test coverage with mocked external dependencies
- **Reliability**: Graceful error handling for external API failures
- **Cost Efficiency**: Optimized for proof-of-concept scale (dozens to hundreds of users)

## Technical Architecture

### Technology Stack
- **Framework**: FastAPI (Python 3.12+)
- **Database**: SQLite for satellite data persistence, session storage, and playlist caching
- **Caching**: In-memory dictionaries for TLE data and pre-cached Spotify playlists
- **Background Tasks**: APScheduler for periodic TLE updates and playlist pre-caching
- **Geographic Data**: Offline country boundaries dataset (Natural Earth or GeoJSON)
- **Authentication**: OAuth 2.0 with Spotify Web API
- **Communication**: HTTP REST API
- **Testing**: pytest with fixtures and mocking
- **Deployment**: Railway cloud platform

### Core Dependencies
```bash
fastapi
uvicorn
sqlite3
spotipy
requests
apscheduler
python-dateutil
shapely           # For geographic point-in-polygon operations
geopandas         # For loading and querying country boundaries
pytest
pytest-asyncio
pytest-mock
ruff
```

## Directory Structure
```
orbital_radio/
├── backend/
│   ├── src/
│   │   ├── main.py                 # FastAPI application entry point
│   │   ├── config.py              # Configuration management
│   │   ├── database.py            # SQLite connection management
│   │   ├── scheduler.py           # Background task scheduling
│   │   │
│   │   ├── api/                   # API route definitions
│   │   │   ├── auth.py           # Endpoints for Spotify authentication (login, callback, logout, refresh)
│   │   │   ├── satellites.py     # Endpoints for satellite data (list, details, TLE, positions)
│   │   │   ├── playlists.py      # Endpoints for playlist generation, next/previous track, mark as played
│   │   │   └── sessions.py       # Endpoints for session management (create, get, delete)
│   │   │   # Each file defines FastAPI routes for a specific domain, calling into services for business logic.
│   │   │
│   │   ├── core/                  # Core business logic
│   │   │   ├── satellite_tracker.py    # TLE data fetching and management
│   │   │   ├── playlist_generator.py   # Region-aware music selection logic
│   │   │   ├── spotify_client.py       # Spotify API wrapper
│   │   │   ├── geographic_mapper.py    # Geographic region mapping with offline boundaries
│   │   │   └── playlist_cache.py       # Playlist pre-caching and management
│   │   │
│   │   ├── models/                # SQLite database models
│   │   │   └── satellite.py       # Defines the Satellite class representing the satellite table/records
│   │   │   # Models define the structure of your database tables and are used for DB operations.
│   │   │
│   │   ├── schemas/               # Pydantic models for API validation/serialization
│   │   │   ├── user.py            # User-related schemas (e.g., UserCreate, UserResponse)
│   │   │   ├── satellite.py       # Satellite-related schemas (e.g., SatelliteResponse)
│   │   │   └── playlist.py        # Playlist and track schemas (e.g., Track, PlaylistResponse)
│   │   │   # Schemas ensure request/response data is well-structured and validated.
│   │   │
│   │   ├── services/              # Service layer for business logic
│   │   │   ├── auth_service.py        # Handles Spotify OAuth, token management
│   │   │   ├── satellite_service.py   # Handles satellite data fetching, TLE updates
│   │   │   ├── playlist_service.py    # Handles playlist generation, next/previous track logic
│   │   │   └── cache_service.py       # Handles in-memory or persistent caching
│   │   │   # Services coordinate between models, core logic, and external APIs.
│   │   │
│   │   └── utils/                 # Utility functions (logging, exceptions, helpers)
│   │
│   ├── tests/                     # Test suite
│   ├── orbital_radio.db          # SQLite database file
│   ├── Dockerfile
│   ├── railway.toml             # Railway deployment configuration
│   ├── pyproject.toml           # uv project configuration
│   └── uv.lock                  # uv lockfile for reproducible installs
```

## Core Components Design

### Satellite TLE Data Manager (`core/satellite_tracker.py`)

**Purpose**: Fetch and manage TLE (Two-Line Element) data from CelesTrak with simple in-memory caching

**Key Methods**:
```python
class SatelliteTLEManager:
    def __init__(self):
        self.tle_cache = {}  # In-memory cache

    def fetch_tle_data(self, satellite_id: str) -> TLEData
    def get_cached_tle(self, satellite_id: str) -> Optional[TLEData]
    def refresh_all_tle_data(self) -> None  # Called by scheduler
    def get_orbital_elements(self, satellite_id: str) -> OrbitalElements
    def generate_simplified_positions(self, satellite_id: str, duration_minutes: int) -> List[Position]
    def get_geographic_region(self, lat: float, lon: float) -> GeographicRegion
```

**Implementation Notes**:
- Fetch TLE data from CelesTrak every 12 hours via APScheduler background task
- Store raw TLE data in simple in-memory dictionary cache
- Generate simplified orbital position predictions for client-side use
- **MVP Focus**: Support only the International Space Station (ISS) initially
- **Future Expansion**: Architecture designed to easily add additional satellites (weather satellites, remote sensing satellites, etc.) by extending the satellite catalog
- Calculations are optimized for smooth, performant frontend animation, not scientific accuracy
- Comprehensive error handling for CelesTrak unavailability

### Geographic Mapper (`core/geographic_mapper.py`)

**Purpose**: Determine which country/region a satellite is currently over using offline geographic boundaries.

**Key Methods**:
```python
class GeographicMapper:
    def __init__(self, boundaries_file: str):
        self.country_boundaries = None  # GeoDataFrame with country polygons
        self.load_boundaries(boundaries_file)

    def load_boundaries(self, file_path: str) -> None
    def get_country_from_coordinates(self, lat: float, lon: float) -> str | None
    def get_nearest_country(self, lat: float, lon: float, max_distance_km: float = 1000, exclude_countries: list[str] = None) -> str
```

**Implementation Notes**:
- Use **offline country boundary data** from Natural Earth (simplified 1:110m dataset) or similar GeoJSON source
- Load country boundaries once at startup and keep in memory for fast lookups
- Use Shapely/GeoPandas for efficient point-in-polygon queries
- For ocean/international waters, find the nearest country within a reasonable distance threshold
- Support excluding countries from nearest-neighbor search to enable cooldown functionality
- Cache boundary data in the repository to avoid external dependencies at runtime
- Provides ISO country codes (e.g., "US", "JP", "BR") for playlist mapping

### Geographic Playlist Generator (`core/playlist_generator.py`)

**Purpose**: Create region-aware track selection using popular music from each nation/region, supporting dynamic next-track selection based on real-time satellite position.

**Key Methods**:
```python
class GeographicPlaylistGenerator:
    def __init__(self, playlist_cache: PlaylistCache, country_cooldown: int = 5):
        self.playlist_cache = playlist_cache
        self.region_playlist_rotation = {}  # Placeholder for future playlist type rotation
        self.country_cooldown = country_cooldown  # Number of songs before country can be reused

    def get_region_top_50_tracks(self, region_code: str) -> list[Track]
    def filter_by_duration(self, tracks: list[Track], min_duration: int = 60, max_duration: int = 480) -> list[Track]
    def deduplicate_tracks(self, tracks: list[Track], played_tracks: set[str]) -> list[Track]
    def is_country_on_cooldown(self, country_code: str, recent_countries: list[str]) -> bool
    def get_next_available_country(self, satellite_position: tuple[float, float], recent_countries: list[str], max_distance_km: int = 2000) -> str
    def get_next_track(self, satellite_position: tuple[float, float], played_tracks: set[str], recent_countries: list[str]) -> Track
    def get_previous_track(self, session_id: str) -> Track
```

**Implementation Notes**:
- For MVP, only use the "Top 50" playlist from Spotify for each nation/region.
- **Relies on pre-cached playlists** from `PlaylistCache` to avoid rate limiting
- The design should allow for easy extension to support additional playlist types (e.g., "Viral 50", "New Music Friday", etc.) in the future.
- When the user requests the next song, dynamically determine the satellite's current position and select a track from the nation/region currently under the satellite.
- **Country Cooldown Logic**: Track the last N countries used (configurable, default 5) and skip them when selecting the next track to prevent oversampling large countries
  - If the satellite is over a country on cooldown, search for the nearest available country (within max distance threshold)
  - Recent countries are stored in session as a FIFO queue/deque of country codes
  - When a track is selected from a country, add that country to the end of the recent countries list
  - If recent countries list exceeds cooldown length, remove the oldest entry
- If the satellite is over the ocean or an unassigned area, select the closest available nation/region (not on cooldown) and use its Top 50 playlist for the next track.
- When the user presses back, play the previously played track from session history (does not affect cooldown state).
- When the user pauses and resumes, playback should resume from the current position in the song (handled via Spotify API controls).
- Generate playlists or tracks based on predicted or real-time orbital paths and nation/region boundaries.
- Include fallback mechanisms for regions with limited Spotify coverage.

### Playlist Cache Manager (`core/playlist_cache.py`)

**Purpose**: Pre-fetch and cache Spotify playlists to avoid rate limiting during active user sessions.

**Key Methods**:
```python
class PlaylistCache:
    def __init__(self, db_path: str):
        self.db_path = db_path  # SQLite database for persistent cache
        self.memory_cache = {}  # In-memory cache for fast access

    def prefetch_all_country_playlists(self, access_token: str) -> None
    def get_cached_playlist(self, country_code: str) -> list[Track] | None
    def is_cache_stale(self, country_code: str, max_age_hours: int = 24) -> bool
    def refresh_stale_caches(self, access_token: str) -> None
    def get_cache_stats(self) -> dict
```

**Implementation Notes**:
- **Pre-cache playlists for all major countries** (150+ countries with Spotify presence) during initialization and via background task
- Store cached playlists in SQLite with timestamps to track freshness
- Refresh caches every 24 hours via APScheduler background task to keep music current
- Load frequently accessed playlists into memory cache for fast retrieval
- Implement exponential backoff for Spotify API rate limits
- Gracefully handle countries without Spotify coverage by maintaining a fallback list
- Reduces API calls during user sessions from hundreds to near-zero
- Cache includes track metadata (ID, name, artist, duration, preview URL)

### Spotify Integration (`core/spotify_client.py`)

**Purpose**: Handle Spotify API interactions for authentication and music search

**Key Methods**:
```python
class SpotifyClient:
    def authenticate_user(self, auth_code: str) -> UserTokens
    def get_user_profile(self, access_token: str) -> UserProfile
    def search_country_playlists(self, country: str, playlist_type: str, access_token: str) -> List[Track]
    def search_tracks(self, query: str, access_token: str, limit: int = 50) -> List[Track]
    def refresh_user_token(self, refresh_token: str) -> UserTokens
```

**Implementation Notes**:
- Use `requests` for all HTTP calls (synchronous)
- Implement basic retry logic for rate limiting
- Store tokens in SQLite-backed session storage
- Handle token refresh automatically
- Focus on search endpoints rather than recommendation APIs
- No persistent token storage beyond session

### Playback Control & Session Management (`services/auth_service.py`)

**Purpose**: Manage playback controls and session state, including pause, resume, next, and previous track functionality.

**Key Methods**:
```python
class SessionManager:
    def __init__(self, db_path: str):
        self.db_path = db_path  # SQLite-backed session storage

    def create_session(self, spotify_tokens: dict) -> str
    def get_session(self, session_id: str) -> dict | None
    def update_session(self, session_id: str, data: dict) -> None
    def add_played_track(self, session_id: str, track_id: str) -> None
    def get_played_tracks(self, session_id: str) -> set[str]
    def add_recent_country(self, session_id: str, country_code: str, max_cooldown: int) -> None
    def get_recent_countries(self, session_id: str) -> list[str]
    def cleanup_expired_sessions(self) -> None
    def get_previous_track(self, session_id: str) -> Track
    def set_playback_position(self, session_id: str, track_id: str, position_ms: int) -> None
    def get_playback_position(self, session_id: str, track_id: str) -> int
```

**Implementation Notes**:
- Store playback position for each track in the session to support pause/resume.
- Maintain a history stack of played tracks for back button functionality.
- Maintain a FIFO list of recently used country codes for cooldown tracking.
- When a track is selected, add its country code to the recent countries list using `add_recent_country()`, which automatically maintains the list size.
- When the user presses next, use the current satellite position to select the next track dynamically, respecting country cooldowns.
- When the user presses back, retrieve the previous track from session history (does not affect cooldown state).
- When the user pauses, store the current playback position; when resuming, continue from that position.

## Data Models

### Satellite Model (SQLite)
```python
class Satellite:
    id: int  # Primary key
    name: str  # "International Space Station"
    norad_id: int  # NORAD catalog number
    category: str  # 'iss', 'weather', 'starlink'
    tle_line1: str  # TLE first line
    tle_line2: str  # TLE second line
    tle_epoch: datetime  # TLE epoch time
    is_active: bool  # Whether to track this satellite
    last_updated: datetime  # When TLE was last refreshed
```

### Session Data (In-Memory)
```python
session_data = {
    "session_id": "uuid4_string",
    "spotify_tokens": {
        "access_token": "...",
        "refresh_token": "...",
        "expires_at": datetime
    },
    "user_profile": {
        "display_name": "User Name",
        "spotify_user_id": "..."
    },
    "current_orbital_session": {
        "satellite_id": "iss",  # MVP: Always ISS
        "start_time": datetime,
        "tle_data": {...},
        "playlist": [...],
        "played_tracks": set(),  # Track IDs to prevent repetition
        "recent_countries": [],  # FIFO list of recently used country codes for cooldown tracking
        "region_playlist_index": {}  # Playlist type rotation per region
    },
    "created_at": datetime,
    "expires_at": datetime
}
```

### Cached Playlist Model (SQLite)
```python
class CachedPlaylist:
    id: int  # Primary key
    country_code: str  # ISO 2-letter code (e.g., "US", "JP")
    playlist_type: str  # "top_50" for MVP
    tracks_json: str  # JSON-serialized list of tracks
    last_updated: datetime  # When playlist was last fetched from Spotify
    track_count: int  # Number of tracks in playlist
    is_valid: bool  # Whether playlist has valid data
```

## API Endpoints Design

### Authentication Endpoints
```
POST /auth/spotify/login     # Initiate Spotify OAuth flow
POST /auth/spotify/callback  # Handle OAuth callback and create session
POST /auth/refresh           # Refresh access tokens
DELETE /auth/logout          # Clear session data
```

### Satellite Endpoints
```
GET /satellites                    # List available satellites
GET /satellites/{id}              # Get satellite details
GET /satellites/{id}/tle          # Get current TLE data for client calculations
GET /satellites/{id}/positions    # Get simplified position predictions
```

### Playlist Endpoints
```
POST /playlists/orbital                      # Generate orbital playlist for session
GET /playlists/orbital/{session_id}         # Get current orbital playlist
POST /playlists/orbital/{session_id}/next   # Get next tracks in sequence
POST /playlists/orbital/{session_id}/played # Mark track as played
```

### Playback Endpoints
```
POST /playback/pause                # Pause current track and store position
POST /playback/resume               # Resume current track from stored position
POST /playback/next                 # Play next track based on current satellite position
POST /playback/previous             # Play previous track from session history
```

### Session Management Endpoints
```
GET /sessions/current           # Get current session data
POST /sessions/{id}/orbital     # Start orbital listening session
DELETE /sessions/{id}           # End session
```

### Health and Status Endpoints
```
GET /health                     # Basic health check
GET /status/satellites          # Satellite data freshness status
GET /status/cache              # Cache statistics
```

## Background Task Management

### APScheduler Configuration
```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()

# Update TLE data every 12 hours (MVP: ISS only)
@scheduler.scheduled_job('interval', hours=12)
async def refresh_tle_data():
    await satellite_service.refresh_all_tle_data()

# Refresh playlist caches every 24 hours to keep music current
@scheduler.scheduled_job('interval', hours=24)
async def refresh_playlist_caches():
    await playlist_cache.refresh_stale_caches()

# Clean up expired sessions every 30 minutes
@scheduler.scheduled_job('interval', minutes=30)
async def cleanup_sessions():
    await session_manager.cleanup_expired_sessions()

# Clean up large played-tracks sets every hour
@scheduler.scheduled_job('interval', hours=1)
async def cleanup_played_tracks():
    await session_manager.cleanup_large_played_sets()
```

## Testing Strategy

### Unit Testing Requirements
- **Minimum 80% code coverage** across all modules with pytest
- **Isolated tests** with mocked external dependencies like for the Spotify API and CelesTrak
- **Async test support** using pytest-asyncio
- **Database tests** using in-memory SQLite for fast execution
- **API tests** using FastAPI TestClient

### Test Structure Example
```python
@pytest.mark.asyncio
async def test_geographic_playlist_generation():
    # Given
    session_data = {"spotify_tokens": {...}, "played_tracks": set()}
    satellite_id = "iss"

    # Mock Spotify search
    with patch('app.core.spotify_client.SpotifyClient') as mock_spotify:
        mock_spotify.search_country_playlists.return_value = mock_tracks

        # When
        playlist = await playlist_generator.generate_orbital_playlist(
            session_data, satellite_id, 90
        )

        # Then
        assert len(playlist.tracks) > 0
        assert all(60 <= track.duration_ms <= 480000 for track in playlist.tracks)
```

## Error Handling & Monitoring

### Exception Hierarchy
```python
class TLEDataError(Exception):
    """TLE data fetching or parsing related errors"""

class SpotifyAPIError(Exception):
    """Spotify API related errors"""

class SessionExpiredError(Exception):
    """User session expired or invalid"""

class PlaylistGenerationError(Exception):
    """Playlist generation related errors"""
```

### Health Checks
```python
@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow(),
        "version": app.version
    }

@app.get("/status/detailed")
def detailed_status():
    return {
        "database": check_database_health(),
        "tle_cache": len(tle_manager.tle_cache),
        "active_sessions": session_manager.count_sessions(),
        "last_tle_update": tle_manager.last_update_time
    }
```

## Configuration Management

### Environment Variables
```python
# Spotify API
SPOTIFY_CLIENT_ID=your_client_id
SPOTIFY_CLIENT_SECRET=your_client_secret
SPOTIFY_REDIRECT_URI=https://your-app.railway.app/auth/spotify/callback

# Application
SECRET_KEY=your_secret_key
ENVIRONMENT=production
LOG_LEVEL=INFO

# Session Management
SESSION_EXPIRE_HOURS=3
MAX_PLAYED_TRACKS_PER_SESSION=500

# Playlist Generation
COUNTRY_COOLDOWN_SONGS=5  # Number of songs before a country can be reused

# Database
DATABASE_PATH=./orbital_radio.db

# Geographic Data
COUNTRY_BOUNDARIES_FILE=./data/country_boundaries.geojson

# Playlist Cache
PLAYLIST_CACHE_MAX_AGE_HOURS=24
PREFETCH_PLAYLISTS_ON_STARTUP=true
```

## Railway Deployment

### Railway Configuration (`railway.toml`)
```toml
[build]
  builder = "DOCKERFILE"

[deploy]
  healthcheckPath = "/health"
  healthcheckTimeout = 300
  restartPolicyType = "ON_FAILURE"
```

### Dockerfile
```dockerfile
# Multi-stage build for optimal caching and smaller image size
FROM python:3.13-slim AS builder

# Copy uv binary from official image (pinned version for reproducibility)
COPY --from=ghcr.io/astral-sh/uv:0.5 /uv /uvx /bin/

# Set working directory
WORKDIR /app

# Enable bytecode compilation for faster startup
ENV UV_COMPILE_BYTECODE=1

# Use the system Python environment instead of creating a virtualenv
ENV UV_PROJECT_ENVIRONMENT=/usr/local

# Install dependencies (leveraging Docker layer caching)
# Copy only dependency files first for better caching
COPY pyproject.toml uv.lock ./

# Install dependencies with cache mount for faster rebuilds
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

# Copy application code
COPY app/ ./app/

# Install the project itself
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# Production stage
FROM python:3.13-slim

# Copy installed dependencies and application from builder
COPY --from=builder /usr/local /usr/local
COPY --from=builder /app /app

WORKDIR /app

# Set environment variables
ENV DATABASE_PATH=/app/data/orbital_radio.db
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Create data directory
RUN mkdir -p /app/data

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=40s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Start application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Documentation Requirements

### Code Documentation
- All Python modules, classes, and functions must use [Google style docstrings](https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings).
- All functions and methods must include type hints using Python 3.12+ syntax (e.g., `List[str]`, `Dict[str, int]`, `| None` for optionals). Prefer classes from the `typing` module over built-in types for type hints to include for mapping types (e.g. `Dict[str, int]`). Do not use `typing.Any` unless absolutely necessary.
- Docstrings should clearly describe the purpose, parameters, return values, and exceptions raised.

### README
- The repository must include a `README.md` at the root level.
- The README should provide:
  - Project overview and purpose
  - Directory structure explanation
  - Setup instructions (Python version, uv installation, dependency installation, environment variables)
  - How to run the backend locally (including database setup)
  - How to run tests

## Development Setup

### Prerequisites
- Python 3.13+
- uv package manager

### Installing uv
```bash
# macOS and Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# Alternative: Install via pip
pip install uv
```

### Project Setup
```bash
# Clone the repository
git clone <repository-url>
cd orbital_radio/backend

# Create virtual environment and install dependencies
uv sync

# Activate the virtual environment (if needed)
source .venv/bin/activate  # macOS/Linux
.venv\Scripts\activate     # Windows

# Run the development server
uv run uvicorn app.main:app --reload

# Run tests
uv run pytest

# Add a new dependency
uv add <package-name>

# Add a development dependency
uv add --dev <package-name>
```

### uv vs Poetry Comparison
- **Faster**: uv is written in Rust and is 10-100x faster than Poetry
- **Simpler**: Single tool that replaces pip, pip-tools, poetry, pyenv, and virtualenv
- **Compatible**: Uses standard `pyproject.toml` format
- **Lockfile**: Uses `uv.lock` for reproducible installs (similar to `poetry.lock`)
- **Commands**:
  - `uv add` → `poetry add`
  - `uv sync` → `poetry install`
  - `uv run` → `poetry run`
  - `uv remove` → `poetry remove`
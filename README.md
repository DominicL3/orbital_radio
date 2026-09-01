# Orbital Radio

Orbital Radio is an anonymous live-radio experience that follows a simulated
ISS orbit. The frontend resolves the simulated latitude/longitude through the
backend's offline country map, and the backend selects an eligible music
station from [Radio Browser](https://www.radio-browser.info/). A single browser
audio element connects directly to the broadcaster; FastAPI never proxies or
stores audio.

## Local development

The backend requires Python 3.12+ and `uv`:

```sh
cd backend
uv sync
uv run uvicorn src.main:app --reload --host 127.0.0.1 --port 8000
```

In another terminal:

```sh
cd frontend
npm install
npm run dev -- --host 127.0.0.1 --port 4174
```

Copy `.env.example` to `.env` when local overrides are needed. The backend has
no account, OAuth, cookie, secret, favorite, or listening-history setup.

## API surface

- `GET /geography/country?latitude=...&longitude=...` returns an ISO alpha-2
  country code or `null` over ocean/unknown coordinates.
- `POST /radio/stations/select` selects one normalized HTTPS MP3/AAC music
  station for a country.
- `POST /radio/stations/{station_uuid}/failed` temporarily deprioritizes a
  station that failed in the browser.
- `/satellites` retains the satellite catalog and TLE endpoints.

Automated tests mock all Radio Browser and broadcaster traffic. The frontend
uses `VITE_API_BASE_URL` when an API host other than the local default is
needed.

## Verification

```sh
cd backend && uv run pytest && uv run ruff check . && uv run ruff format --check .
cd frontend && npm run test:unit && npm run type-check && npm run build
```

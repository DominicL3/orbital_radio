# Orbital Radio Frontend

Vue 3 + Vite + Cesium frontend for Orbital Radio. It shows a simulated ISS trajectory and resolves the simulated position through the anonymous backend to play live HTTPS MP3/AAC stations from Radio Browser. The backend selects and normalizes station metadata; the browser connects directly to the broadcaster and owns one audio element for the page visit.

## Run locally

Run these commands in a terminal from the repository root:

```bash
cd frontend
npm install
npm run dev
```

Vite prints a local URL, normally [http://localhost:5173](http://localhost:5173). Open that URL in a browser to use the globe.

### Backend API

Set `VITE_API_BASE_URL` when the backend is not served from the same origin. For
local development, start FastAPI on `http://127.0.0.1:8000` and use:

```bash
VITE_API_BASE_URL=http://127.0.0.1:8000
```

The first land-country lookup must remain stable for three wall-clock seconds
before the panel enables Play. A user gesture starts the live stream. Later
country changes can switch stations automatically after a successful start;
ocean and unknown positions leave the current broadcaster untouched. Pause
detaches the stream and Play reconnects at the live edge. No account, cookie,
favorite, listening history, or local-storage preference is used.

### Google Satellite imagery and terrain

This branch uses Cesium ion's Google Maps 2D Satellite with Labels imagery and
Cesium World Terrain. Google provides the country borders and labels in the
imagery, so this branch intentionally does not add an external country overlay.
Before starting Vite, create `frontend/.env.local` with a read-only Cesium ion
token:

```bash
VITE_CESIUM_ION_TOKEN=your_token_here
```

Configure the token with the public `assets:read` scope and access to both
`Google Maps 2D Satellite with Labels` (asset `3830183`) and `Cesium World
Terrain` (asset `1`). The token is intentionally not committed. Without it,
the globe shows an in-app setup notice instead of requesting satellite imagery.

Do not open `frontend/index.html` directly in a browser (`file://…`). Vite must serve the app so it can compile the TypeScript entrypoint and provide Cesium's static assets.

To expose the development server to another device on the same network:

```bash
npm run dev -- --host 0.0.0.0
```

## Verify

```bash
npm run typecheck
npm run lint
npm test
npm run build
npm run test:browser
```

The first browser-test run may require `npx playwright install chromium`.

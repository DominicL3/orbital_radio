# Orbital Radio Frontend

Vue 3 + Vite + Cesium visual prototype for Orbital Radio. It shows a simulated ISS trajectory and a fixture-driven radio panel. It does **not** provide live satellite or Spotify playback data yet.

## Run locally

Run these commands in a terminal from the repository root:

```bash
cd frontend
npm install
npm run dev
```

Vite prints a local URL, normally [http://localhost:5173](http://localhost:5173). Open that URL in a browser to use the globe.

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

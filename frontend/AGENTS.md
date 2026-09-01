# Orbital Radio Frontend

For project-wide architecture, deployment, and session-policy decisions, see [`../CLAUDE.md`](../CLAUDE.md). This file contains frontend-specific guidance only.

## Product decisions

- Use Vue 3, Vite, and TypeScript. Cesium owns the globe; React, Next.js, and D3 are not part of this app.
- The visual language is cinematic and dark: near-black panels, restrained technical type, cool orbital blue, and a warm radio accent. The layout is desktop-first with responsive overlays.
- Cesium is initialized exactly once inside `src/features/globe/CesiumGlobe.vue`. Vue owns application state and controls; it must not make Cesium entities deeply reactive.
- The current ISS motion is a demo simulation. Always label it as such. All position providers implement `OrbitPositionSource` so a later satellite.js/TLE provider can replace the demo source without changing the UI.
- Model satellites as catalog entries even though the MVP catalog contains only the ISS. The intended future scale is a curated set of major LEO satellites, not every member of a constellation.
- The radio panel uses the anonymous backend radio API and owns one live HTMLAudioElement for each page visit. Audio streams are direct broadcaster HTTPS MP3/AAC connections; the frontend never proxies or relays audio.

## Boundaries

- `src/contracts/` defines shared application data; feature code consumes those types and must not duplicate them. Fixtures are test-only and must not stand in for provider behavior.
- `src/features/globe/` exclusively owns Cesium lifecycle, entities, and camera actions.
- `src/features/explorer/` owns overlays and simulation controls. It communicates with the globe through typed props/events/exposed methods only.
- `src/features/radio/` owns station API mapping, the one-element live player, and station presentation. Keep country dwell timing in wall-clock milliseconds, independent of simulation speed.

## Commit messages

- Use short, imperative sentence-case subjects that describe the completed change, capitalizing the first word plus proper nouns and acronyms only. For example: `Define anonymous radio API behavior` or `Remove decorative space confetti`.
- Do not use Conventional Commit prefixes such as `feat:`, `fix:`, `chore:`, or scopes.

# Orbital Radio Frontend

## Locked product decisions

- Use Vue 3, Vite, and TypeScript. Cesium owns the globe; React, Next.js, and D3 are not part of this app.
- The visual language is cinematic and dark: near-black panels, restrained technical type, cool orbital blue, and a warm radio accent. The layout is desktop-first with responsive overlays.
- Cesium is initialized exactly once inside `src/features/globe/CesiumGlobe.vue`. Vue owns application state and controls; it must not make Cesium entities deeply reactive.
- The current ISS motion is a demo simulation. Always label it as such. All position providers implement `OrbitPositionSource` so a later satellite.js/TLE provider can replace the demo source without changing the UI.
- Model satellites as catalog entries even though the MVP catalog contains only the ISS. The intended future scale is a curated set of major LEO satellites, not every member of a constellation.
- The radio panel is fixture-driven. Spotify OAuth and real playback are explicitly deferred.

## Boundaries

- `src/contracts/` and `src/fixtures/` define shared data; feature code consumes them and must not duplicate their types.
- `src/features/globe/` exclusively owns Cesium lifecycle, entities, and camera actions.
- `src/features/explorer/` owns overlays and simulation controls. It communicates with the globe through typed props/events/exposed methods only.
- `src/features/radio/` owns mock radio state and presentation.

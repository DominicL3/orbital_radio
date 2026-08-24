<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import type { RadioState } from '@/contracts/radio'
import type { SatelliteCatalogEntry, SimulationState } from '@/contracts/satellite'
import { issCatalogEntry, satelliteCatalog } from '@/fixtures/iss'
import { mockRadioTracks } from '@/fixtures/radio'
import CesiumGlobe from '@/features/globe/CesiumGlobe.vue'
import ExplorerControls from '@/features/explorer/ExplorerControls.vue'
import SatelliteInfoPanel from '@/features/explorer/SatelliteInfoPanel.vue'
import RadioPanel from '@/features/radio/RadioPanel.vue'

type GlobeHandle = {
  focusSatellite?: () => void
}

const globeRef = ref<GlobeHandle | null>(null)
const selectedSatelliteId = ref<string | null>(issCatalogEntry.id)
const showOrbitPath = ref(true)
const simulation = reactive<SimulationState>({ isPlaying: true, speed: 1 })

const selectedSatellite = computed<SatelliteCatalogEntry>(() => {
  return satelliteCatalog.find((satellite) => satellite.id === selectedSatelliteId.value) ?? issCatalogEntry
})

const radioState = reactive<RadioState>({
  status: 'ready',
  isPlaying: false,
  track: mockRadioTracks[0] ?? null,
})
const radioTrackIndex = ref(0)

function toggleSimulation() {
  simulation.isPlaying = !simulation.isPlaying
}

function setSimulationSpeed(speed: SimulationState['speed']) {
  simulation.speed = speed
}

function focusSelectedSatellite() {
  globeRef.value?.focusSatellite?.()
}

function selectSatellite(satellite: SatelliteCatalogEntry | string | null) {
  if (!satellite) return
  selectedSatelliteId.value = typeof satellite === 'string' ? satellite : satellite.id
}

function toggleRadio() {
  radioState.isPlaying = !radioState.isPlaying
}

function nextTrack() {
  if (!mockRadioTracks.length) {
    radioState.status = 'empty'
    radioState.track = null
    return
  }

  radioTrackIndex.value = (radioTrackIndex.value + 1) % mockRadioTracks.length
  radioState.track = mockRadioTracks[radioTrackIndex.value] ?? null
  radioState.status = radioState.track ? 'ready' : 'empty'
}
</script>

<template>
  <main class="orbital-app">
    <CesiumGlobe
      ref="globeRef"
      class="globe-layer"
      :satellite="selectedSatellite"
      :is-playing="simulation.isPlaying"
      :speed="simulation.speed"
      :show-orbit-path="showOrbitPath"
      @satellite-selected="selectSatellite"
    />

    <div class="vignette" aria-hidden="true" />

    <header class="topbar">
      <a class="wordmark" href="/" aria-label="Orbital Radio home">
        <span class="wordmark-orbit" aria-hidden="true"><span /></span>
        <span>ORBITAL <em>RADIO</em></span>
      </a>
      <div class="topbar-meta">
        <span class="live-indicator"><span />ON AIR / LIVE VIEW</span>
        <span class="topbar-divider" aria-hidden="true" />
        <span>01 TARGET ONLINE</span>
      </div>
    </header>

    <section class="hero-copy" aria-label="Orbital Radio introduction">
      <p class="hero-kicker"><span class="kicker-wave" aria-hidden="true">〰</span> LOW EARTH ORBIT / 51.6° INCLINATION</p>
      <h2>ISS <span>GROOVE</span></h2>
      <p class="hero-description">A moving mixtape drawn across the night side of Earth.</p>
    </section>

    <aside class="target-overlay">
      <SatelliteInfoPanel :satellite="selectedSatellite" @focus="focusSelectedSatellite" />
      <ExplorerControls
        :is-playing="simulation.isPlaying"
        :speed="simulation.speed"
        :show-orbit-path="showOrbitPath"
        @toggle-play="toggleSimulation"
        @set-speed="setSimulationSpeed"
        @toggle-orbit-path="showOrbitPath = !showOrbitPath"
      />
    </aside>

    <aside class="radio-overlay">
      <RadioPanel :state="radioState" @toggle-play="toggleRadio" @next-track="nextTrack" />
    </aside>

    <footer class="status-footer">
      <div class="legend-item"><span class="legend-dot" /> ISS / SIMULATED POSITION</div>
      <div class="footer-note">DATA SOURCE · DEMO ORBITAL PROVIDER</div>
      <div class="coordinates">EARTH / <span>ROTATING</span></div>
    </footer>
  </main>
</template>

<style scoped>
.orbital-app {
  background: #100b24;
  color: #fff5fc;
  min-height: 100vh;
  overflow: hidden;
  position: relative;
}

.globe-layer {
  inset: 0;
  position: absolute;
  z-index: 0;
}

.vignette {
  background:
    radial-gradient(circle at 16% 48%, rgba(255, 82, 170, 0.18), transparent 23%),
    radial-gradient(circle at 85% 24%, rgba(89, 224, 255, 0.18), transparent 24%),
    linear-gradient(180deg, rgba(11, 5, 28, 0.76), transparent 25%, transparent 68%, rgba(10, 4, 25, 0.78)),
    linear-gradient(90deg, rgba(14, 5, 34, 0.68), transparent 33%, transparent 74%, rgba(8, 5, 29, 0.28));
  inset: 0;
  pointer-events: none;
  position: absolute;
  z-index: 1;
}

.topbar,
.hero-copy,
.target-overlay,
.radio-overlay,
.status-footer {
  position: absolute;
  z-index: 2;
}

.topbar {
  align-items: center;
  display: flex;
  justify-content: space-between;
  left: 32px;
  right: 32px;
  top: 28px;
}

.wordmark {
  align-items: center;
  color: #fff6fc;
  display: inline-flex;
  font-size: 13px;
  font-weight: 700;
  gap: 10px;
  letter-spacing: 0.16em;
  text-decoration: none;
}

.wordmark em {
  color: #ff72c3;
  font-style: normal;
  font-weight: 400;
}

.wordmark-orbit {
  border: 1px solid rgba(111, 231, 255, 0.95);
  border-radius: 50%;
  display: inline-block;
  height: 20px;
  position: relative;
  transform: rotate(-32deg);
  width: 27px;
}

.wordmark-orbit::before {
  border: 1px solid rgba(255, 109, 188, 0.52);
  border-radius: 50%;
  content: '';
  inset: 3px -4px;
  position: absolute;
}

.wordmark-orbit span {
  background: #ffe56e;
  border-radius: 50%;
  box-shadow: 0 0 9px rgba(255, 229, 110, 0.9);
  height: 4px;
  position: absolute;
  right: -2px;
  top: 1px;
  width: 4px;
}

.topbar-meta {
  align-items: center;
  color: rgba(233, 213, 250, 0.58);
  display: flex;
  font-size: 9px;
  font-weight: 700;
  gap: 13px;
  letter-spacing: 0.16em;
}

.live-indicator {
  align-items: center;
  color: #7ff7e9;
  display: inline-flex;
  gap: 6px;
}

.live-indicator span {
  background: #7ff7e9;
  border-radius: 50%;
  box-shadow: 0 0 9px rgba(158, 214, 249, 0.8);
  height: 5px;
  width: 5px;
}

.topbar-divider {
  background: rgba(193, 220, 239, 0.22);
  height: 13px;
  width: 1px;
}

.hero-copy {
  left: 32px;
  top: 26%;
}

.hero-kicker {
  color: rgba(190, 239, 252, 0.76);
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 0.19em;
  margin: 0 0 10px;
}

.kicker-wave { color: #ff75c4; font-size: 1.35em; letter-spacing: -0.18em; margin-right: 0.5rem; }

h2 {
  font-size: clamp(40px, 5.2vw, 74px);
  font-weight: 800;
  letter-spacing: -0.075em;
  line-height: 0.95;
  margin: 0;
}

h2 span {
  background: linear-gradient(90deg, #ff69bb, #ffd465 48%, #6beeff);
  background-clip: text;
  color: transparent;
  display: block;
  font-size: 0.42em;
  font-weight: 700;
  letter-spacing: 0.24em;
  margin-top: 12px;
}

.hero-description {
  color: rgba(238, 221, 251, 0.8);
  font-size: 12px;
  margin: 18px 0 0;
}

.target-overlay {
  bottom: 78px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  left: 32px;
  width: min(375px, calc(100vw - 64px));
}

.radio-overlay {
  bottom: 78px;
  right: 32px;
  width: min(330px, calc(100vw - 64px));
}

.status-footer {
  align-items: center;
  bottom: 25px;
  color: rgba(181, 211, 232, 0.45);
  display: flex;
  font-size: 9px;
  font-weight: 700;
  gap: 24px;
  left: 32px;
  letter-spacing: 0.14em;
  right: 32px;
}

.legend-item {
  align-items: center;
  display: inline-flex;
  gap: 7px;
}

.legend-dot {
  background: #ff69bd;
  border-radius: 50%;
  box-shadow: 0 0 10px rgba(255, 105, 189, 0.9);
  display: inline-block;
  height: 5px;
  width: 5px;
}

.footer-note {
  margin-left: auto;
}

.coordinates span {
  color: #79eeff;
}

@media (max-width: 760px) {
  .topbar,
  .hero-copy,
  .target-overlay,
  .radio-overlay,
  .status-footer {
    left: 18px;
    right: 18px;
  }

  .topbar {
    top: 18px;
  }

  .topbar-meta span:last-child,
  .topbar-divider,
  .footer-note {
    display: none;
  }

  .hero-copy {
    top: 17%;
  }

  .target-overlay {
    bottom: 70px;
    width: auto;
  }

  .radio-overlay {
    bottom: 18px;
    left: auto;
    width: min(250px, calc(100vw - 36px));
  }

  .status-footer {
    bottom: 18px;
    right: auto;
  }

  .coordinates {
    display: none;
  }
}

@media (max-width: 540px) {
  .hero-copy {
    top: 14%;
  }

  .target-overlay {
    bottom: 80px;
  }

  .radio-overlay {
    bottom: 18px;
    left: 18px;
    right: 18px;
    width: auto;
  }

  .status-footer {
    display: none;
  }
}
</style>

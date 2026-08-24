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
    </header>

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
.target-overlay,
.radio-overlay {
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

.target-overlay {
  bottom: 32px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  left: 32px;
  width: min(375px, calc(100vw - 64px));
}

.radio-overlay {
  bottom: 32px;
  right: 32px;
  width: min(330px, calc(100vw - 64px));
}

@media (max-width: 760px) {
  .topbar,
  .target-overlay,
  .radio-overlay {
    left: 18px;
    right: 18px;
  }

  .topbar {
    top: 18px;
  }

  .target-overlay {
    bottom: 18px;
    width: auto;
  }

  .radio-overlay {
    bottom: 18px;
    left: auto;
    width: min(250px, calc(100vw - 36px));
  }

}

@media (max-width: 540px) {
  .target-overlay {
    bottom: 80px;
  }

  .radio-overlay {
    bottom: 18px;
    left: 18px;
    right: 18px;
    width: auto;
  }
}
</style>

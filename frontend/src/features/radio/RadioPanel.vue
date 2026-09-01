<script setup lang="ts">
import { ref, watch } from 'vue'
import type { RadioState, RadioStatus } from '@/contracts/radio'

const props = defineProps<{
  state: RadioState
}>()

const emit = defineEmits<{
  (event: 'toggle-play'): void
  (event: 'next-station'): void
}>()

const faviconFailed = ref(false)
const lastStationUuid = ref<string | null>(null)

watch(() => props.state.station?.stationUuid ?? null, (stationUuid) => {
  if (stationUuid !== lastStationUuid.value) {
    lastStationUuid.value = stationUuid
    faviconFailed.value = false
  }
}, { immediate: true })

const statusLabels: Record<RadioStatus, string> = {
  waiting: 'WAITING',
  connecting: 'CONNECTING',
  playing: 'ON AIR',
  paused: 'PAUSED',
  retrying: 'RETRYING',
  unavailable: 'UNAVAILABLE',
}

const canPlay = () => Boolean(props.state.countryCode) && props.state.status !== 'connecting' && props.state.status !== 'retrying'
</script>

<template>
  <section class="radio-panel" aria-label="Orbital radio">
    <div class="panel-heading">
      <div>
        <p class="eyebrow">ORBITAL RADIO</p>
        <h2>Live signal in transit</h2>
      </div>
      <span class="live-mark" :class="`is-${props.state.status}`">
        <span class="live-dot" aria-hidden="true"></span>
        {{ statusLabels[props.state.status] }}
      </span>
    </div>

    <div v-if="!props.state.station" class="state-message" :class="{ 'state-message--empty': props.state.status === 'unavailable' }" role="status" aria-live="polite">
      <span v-if="props.state.status === 'connecting' || props.state.status === 'retrying'" class="pulse-bars" aria-hidden="true"><i></i><i></i><i></i></span>
      <span v-else class="empty-orbit" aria-hidden="true">∅</span>
      <span>{{ props.state.status === 'unavailable' ? 'No transmission available' : props.state.countryCode ? 'Ready for a live station' : 'Waiting for a land signal' }}</span>
      <small v-if="props.state.status === 'unavailable'">Check back when the next signal arrives.</small>
    </div>

    <template v-if="props.state.station">
      <div class="station">
        <div class="artwork" role="img" :aria-label="`${props.state.station.name} station icon`">
          <img
            v-if="props.state.station.faviconUrl && !faviconFailed"
            :src="props.state.station.faviconUrl"
            alt=""
            @error="faviconFailed = true"
          >
          <span v-else class="artwork-glyph" aria-hidden="true">♫</span>
          <span class="artwork-star artwork-star--one" aria-hidden="true">✦</span>
          <span class="artwork-star artwork-star--two" aria-hidden="true">✦</span>
          <span class="artwork-ring artwork-ring--one" aria-hidden="true"></span>
          <span class="artwork-ring artwork-ring--two" aria-hidden="true"></span>
        </div>
        <div class="station-copy">
          <p class="station-kicker">LIVE STATION</p>
          <h3>{{ props.state.station.name }}</h3>
          <p class="context"><span class="context-marker" aria-hidden="true">◎</span> {{ props.state.station.countryCode }}</p>
          <ul v-if="props.state.station.tags.length" class="tags" aria-label="Station tags">
            <li v-for="tag in props.state.station.tags.slice(0, 4)" :key="tag">{{ tag }}</li>
          </ul>
        </div>
      </div>

      <div class="signal-line" aria-hidden="true"><i v-for="bar in 36" :key="bar" :class="{ 'is-playing': props.state.isPlaying }" /></div>

    </template>

    <div class="controls">
      <button
        class="control-button control-button--next"
        type="button"
        aria-label="Next station"
        :disabled="!props.state.countryCode || !props.state.station || props.state.status === 'connecting' || props.state.status === 'retrying'"
        @click="emit('next-station')"
      >
        <span aria-hidden="true">↠</span>
      </button>
      <button
        class="control-button control-button--play"
        type="button"
        :aria-label="props.state.isPlaying ? 'Pause radio' : 'Play radio'"
        :disabled="!canPlay()"
        @click="emit('toggle-play')"
      >
        <span aria-hidden="true">{{ props.state.isPlaying ? 'Ⅱ' : '▶' }}</span>
      </button>
      <span class="control-hint">{{ props.state.isPlaying ? 'RECEIVING' : props.state.status === 'paused' ? 'PAUSED' : 'LIVE RADIO' }}</span>
    </div>
  </section>
</template>

<style scoped>
.radio-panel {
  width: min(100%, 23rem);
  padding: 1.15rem 1.2rem 1rem;
  border: 1px solid rgba(255, 148, 214, 0.38);
  border-radius: 1.2rem;
  color: #fff3fb;
  background: linear-gradient(145deg, rgba(53, 18, 76, 0.94), rgba(11, 18, 55, 0.94));
  box-shadow: 0 1.25rem 3.5rem rgba(0, 0, 0, 0.35), inset 0 1px rgba(255, 255, 255, 0.13), 0 0 2.5rem rgba(231, 64, 180, 0.13);
  backdrop-filter: blur(18px);
}

.panel-heading,
.controls {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.eyebrow,
.station-kicker,
.control-hint {
  margin: 0;
  letter-spacing: 0.14em;
  font-size: 0.58rem;
  font-weight: 700;
}

.eyebrow { color: #85f3ef; }
h2 { margin: 0.26rem 0 0; font-size: 1.03rem; font-weight: 600; letter-spacing: -0.02em; }

.live-mark { display: inline-flex; align-items: center; gap: 0.38rem; color: #ffd76b; font-size: 0.58rem; font-weight: 700; letter-spacing: 0.12em; }
.live-mark.is-waiting, .live-mark.is-paused { color: #8fa8c3; }
.live-mark.is-connecting, .live-mark.is-retrying { color: #e6a36b; }
.live-mark.is-unavailable { color: #d686a9; }
.live-dot { width: 0.42rem; height: 0.42rem; border-radius: 999px; background: currentColor; box-shadow: 0 0 0 0.2rem color-mix(in srgb, currentColor 14%, transparent); }
.live-mark.is-playing .live-dot { animation: blink 2s ease-in-out infinite; }

.station { display: flex; gap: 1rem; margin: 1.35rem 0 0.75rem; }
.artwork { position: relative; flex: none; display: grid; place-items: center; width: 5.2rem; height: 5.2rem; overflow: hidden; border: 1px solid rgba(255, 231, 124, 0.72); border-radius: 50%; background: conic-gradient(from 25deg, #ffdc68, #ff67b7 28%, #704dff 52%, #42d7ed 74%, #ffdc68); background-size: cover; box-shadow: 0 0 0 5px rgba(255, 255, 255, 0.05), 0 0.5rem 1.3rem rgba(255, 65, 167, 0.34); }
.artwork img { width: 100%; height: 100%; object-fit: cover; }
.artwork::before { position: absolute; width: 68%; height: 68%; content: ''; border: 1px solid rgba(27, 11, 76, 0.55); border-radius: 50%; background: repeating-radial-gradient(circle, rgba(22, 11, 57, 0.2) 0 2px, transparent 3px 5px), #31115b; pointer-events: none; }
.artwork::after { position: absolute; inset: 0; content: ''; background: linear-gradient(135deg, rgba(255, 255, 255, 0.35), transparent 35%); pointer-events: none; }
.artwork-glyph { z-index: 2; color: #fff3b2; font-size: 1.25rem; line-height: 1; text-shadow: 0 1px 5px #150527; }
.artwork-star { color: #fff3b2; font-size: 0.55rem; position: absolute; z-index: 2; }
.artwork-star--one { right: 0.55rem; top: 0.7rem; }.artwork-star--two { bottom: 0.62rem; left: 0.68rem; }
.artwork-ring { position: absolute; z-index: 1; border: 1px solid rgba(255, 234, 206, 0.38); border-radius: 50%; transform: rotate(-35deg); }
.artwork-ring--one { width: 5.5rem; height: 1.6rem; }
.artwork-ring--two { width: 1.8rem; height: 5.5rem; opacity: 0.55; }
.station-copy { min-width: 0; padding-top: 0.1rem; }
.station-kicker { color: #ff9ad2; }
h3 { overflow: hidden; margin: 0.32rem 0 0.15rem; font-size: 1.12rem; font-weight: 600; text-overflow: ellipsis; white-space: nowrap; }
.context { display: flex; align-items: center; gap: 0.3rem; margin: 0.55rem 0 0; color: #e4d8ed; font-size: 0.64rem; letter-spacing: 0.04em; }
.context-marker { color: #75f3ee; font-size: 0.8rem; }
.tags { display: flex; flex-wrap: wrap; gap: 0.3rem; margin: 0.55rem 0 0; padding: 0; list-style: none; }
.tags li { padding: 0.18rem 0.34rem; border: 1px solid rgba(117, 241, 236, 0.22); border-radius: 0.3rem; color: #b9d9de; font-size: 0.55rem; text-transform: uppercase; letter-spacing: 0.06em; }

.signal-line { align-items: flex-end; display: flex; justify-content: space-between; height: 1.55rem; margin-bottom: 0.25rem; overflow: hidden; padding: 0 0.1rem; }
.signal-line i { flex: 0 0 0.14rem; width: 0.14rem; height: var(--rest-height); border-radius: 999px; background: linear-gradient(to top, #ff80c9, #77f6ed); opacity: 0.58; transform-origin: bottom; }
.signal-line i:nth-child(5n + 1) { --rest-height: 26%; --peak-height: 74%; --tempo: 860ms; }
.signal-line i:nth-child(5n + 2) { --rest-height: 61%; --peak-height: 96%; --tempo: 540ms; }
.signal-line i:nth-child(5n + 3) { --rest-height: 38%; --peak-height: 84%; --tempo: 690ms; }
.signal-line i:nth-child(5n + 4) { --rest-height: 77%; --peak-height: 100%; --tempo: 620ms; }
.signal-line i:nth-child(5n) { --rest-height: 18%; --peak-height: 57%; --tempo: 930ms; }
.signal-line i.is-playing { animation: equalize var(--tempo) ease-in-out infinite alternate; }
.signal-line i.is-playing:nth-child(3n) { animation-delay: -180ms; }
.signal-line i.is-playing:nth-child(4n) { animation-delay: -340ms; }

.controls { justify-content: center; gap: 0.8rem; margin-top: 1rem; }
.control-button { display: grid; place-items: center; border: 0; cursor: pointer; color: #dce9f5; background: transparent; transition: color 0.2s ease, transform 0.2s ease, background 0.2s ease; }
.control-button:hover:not(:disabled) { color: #ffb2da; transform: translateY(-1px); }
.control-button:focus-visible { outline: 2px solid #78f1ec; outline-offset: 3px; }
.control-button:disabled { cursor: not-allowed; opacity: 0.45; }
.control-button--play { width: 2.8rem; height: 2.8rem; border-radius: 50%; color: #281040; background: linear-gradient(145deg, #ffe36e, #ff9ccf); box-shadow: 0 0.3rem 1rem rgba(255, 112, 190, 0.36); }
.control-button--play:hover:not(:disabled) { color: #170427; background: #fff09c; }
.control-button--next { order: 2; font-size: 1.35rem; }
.control-button--play { order: 1; }
.control-hint { order: 3; min-width: 4.2rem; color: #71869c; }

.state-message { display: flex; align-items: center; justify-content: center; gap: 0.55rem; min-height: 9.2rem; color: #b0c0d2; font-size: 0.82rem; }
.state-message--empty { flex-direction: column; gap: 0.35rem; text-align: center; }
.state-message small { color: #6f8297; font-size: 0.67rem; }
.empty-orbit { color: #708aa4; font-size: 1.5rem; }
.pulse-bars { display: inline-flex; align-items: center; gap: 0.18rem; height: 1.3rem; }
.pulse-bars i { display: block; width: 0.18rem; height: 0.65rem; border-radius: 99px; background: #e6a36b; animation: bars 0.8s ease-in-out infinite alternate; }
.pulse-bars i:nth-child(2) { animation-delay: 0.18s; }
.pulse-bars i:nth-child(3) { animation-delay: 0.34s; }

@keyframes blink { 0%, 100% { opacity: 0.55; } 50% { opacity: 1; } }
@keyframes bars { to { height: 1.15rem; opacity: 0.48; } }
@keyframes equalize { to { height: var(--peak-height); opacity: 1; } }

@media (prefers-reduced-motion: no-preference) { .artwork { animation: record-spin 15s linear infinite; } }
@keyframes record-spin { to { transform: rotate(360deg); } }

@media (max-width: 38rem) {
  .radio-panel { width: 100%; }
}
</style>

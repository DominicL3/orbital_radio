<script setup lang="ts">
import type { RadioState } from '@/contracts/radio'

const props = defineProps<{
  state: RadioState
}>()

const emit = defineEmits<{
  (event: 'toggle-play'): void
  (event: 'next-track'): void
}>()

const togglePlay = () => emit('toggle-play')
const nextTrack = () => emit('next-track')
</script>

<template>
  <section class="radio-panel" aria-label="Orbital radio">
    <div class="panel-heading">
      <div>
        <p class="eyebrow">ORBITAL RADIO</p>
        <h2>Signal in transit</h2>
      </div>
      <span class="live-mark" :class="`is-${props.state.status}`">
        <span class="live-dot" aria-hidden="true"></span>
        {{ props.state.status === 'ready' ? 'ON AIR' : props.state.status.toUpperCase() }}
      </span>
    </div>

    <div v-if="props.state.status === 'loading'" class="state-message" role="status" aria-live="polite">
      <span class="pulse-bars" aria-hidden="true"><i></i><i></i><i></i></span>
      <span>Finding a signal…</span>
    </div>

    <div v-else-if="props.state.status === 'empty' || !props.state.track" class="state-message state-message--empty" role="status">
      <span class="empty-orbit" aria-hidden="true">∅</span>
      <span>No transmission available</span>
      <small>Check back when the next signal arrives.</small>
    </div>

    <template v-else>
        <div class="track">
          <div class="artwork" :style="props.state.track.artworkUrl ? { backgroundImage: `url(${props.state.track.artworkUrl})` } : undefined" role="img" :aria-label="`${props.state.track.title} artwork`">
          <span v-if="!props.state.track.artworkUrl" class="artwork-glyph" aria-hidden="true">♫</span>
          <span class="artwork-star artwork-star--one" aria-hidden="true">✦</span>
          <span class="artwork-star artwork-star--two" aria-hidden="true">✦</span>
          <span class="artwork-ring artwork-ring--one" aria-hidden="true"></span>
          <span class="artwork-ring artwork-ring--two" aria-hidden="true"></span>
        </div>
        <div class="track-copy">
          <p class="track-kicker">NOW PLAYING</p>
          <h3>{{ props.state.track.title }}</h3>
          <p class="artist">{{ props.state.track.artist }}</p>
          <p class="context"><span class="context-marker" aria-hidden="true">◎</span> {{ props.state.track.country }} <span class="context-separator">·</span> {{ props.state.track.countryCode }}</p>
        </div>
      </div>

      <div class="signal-line" aria-hidden="true"><i v-for="bar in 36" :key="bar" :class="{ 'is-playing': props.state.isPlaying }" /></div>
      <div class="progress-track" aria-hidden="true"><span :class="{ 'is-playing': props.state.isPlaying }"></span></div>
      <div class="time-row"><span>LIVE SIGNAL</span><span>{{ props.state.track.durationLabel }}</span></div>

      <div class="controls">
        <button class="control-button control-button--skip" type="button" aria-label="Skip track" @click="nextTrack">
          <span aria-hidden="true">↠</span>
        </button>
        <button class="control-button control-button--play" type="button" :aria-label="props.state.isPlaying ? 'Pause radio' : 'Play radio'" @click="togglePlay">
          <span aria-hidden="true">{{ props.state.isPlaying ? 'Ⅱ' : '▶' }}</span>
        </button>
        <span class="control-hint">{{ props.state.isPlaying ? 'RECEIVING' : 'PAUSED' }}</span>
      </div>
    </template>
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
.time-row,
.controls {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.eyebrow,
.track-kicker,
.time-row,
.control-hint {
  margin: 0;
  letter-spacing: 0.14em;
  font-size: 0.58rem;
  font-weight: 700;
}

.eyebrow { color: #85f3ef; }
h2 { margin: 0.26rem 0 0; font-size: 1.03rem; font-weight: 600; letter-spacing: -0.02em; }

.live-mark { display: inline-flex; align-items: center; gap: 0.38rem; color: #ffd76b; font-size: 0.58rem; font-weight: 700; letter-spacing: 0.12em; }
.live-mark.is-loading { color: #8fa8c3; }
.live-mark.is-empty { color: #728298; }
.live-dot { width: 0.42rem; height: 0.42rem; border-radius: 999px; background: currentColor; box-shadow: 0 0 0 0.2rem color-mix(in srgb, currentColor 14%, transparent); }
.is-ready .live-dot { animation: blink 2s ease-in-out infinite; }

.track { display: flex; gap: 1rem; margin: 1.35rem 0 0.75rem; }
.artwork { position: relative; flex: none; display: grid; place-items: center; width: 5.2rem; height: 5.2rem; overflow: hidden; border: 1px solid rgba(255, 231, 124, 0.72); border-radius: 50%; background: conic-gradient(from 25deg, #ffdc68, #ff67b7 28%, #704dff 52%, #42d7ed 74%, #ffdc68); background-size: cover; box-shadow: 0 0 0 5px rgba(255, 255, 255, 0.05), 0 0.5rem 1.3rem rgba(255, 65, 167, 0.34); }
.artwork::before { position: absolute; width: 68%; height: 68%; content: ''; border: 1px solid rgba(27, 11, 76, 0.55); border-radius: 50%; background: repeating-radial-gradient(circle, rgba(22, 11, 57, 0.2) 0 2px, transparent 3px 5px), #31115b; }
.artwork::after { position: absolute; inset: 0; content: ''; background: linear-gradient(135deg, rgba(255, 255, 255, 0.35), transparent 35%); }
.artwork-glyph { z-index: 2; color: #fff3b2; font-size: 1.25rem; line-height: 1; text-shadow: 0 1px 5px #150527; }
.artwork-star { color: #fff3b2; font-size: 0.55rem; position: absolute; z-index: 2; }
.artwork-star--one { right: 0.55rem; top: 0.7rem; }.artwork-star--two { bottom: 0.62rem; left: 0.68rem; }
.artwork-ring { position: absolute; z-index: 1; border: 1px solid rgba(255, 234, 206, 0.38); border-radius: 50%; transform: rotate(-35deg); }
.artwork-ring--one { width: 5.5rem; height: 1.6rem; }
.artwork-ring--two { width: 1.8rem; height: 5.5rem; opacity: 0.55; }
.track-copy { min-width: 0; padding-top: 0.1rem; }
.track-kicker { color: #ff9ad2; }
h3 { overflow: hidden; margin: 0.32rem 0 0.15rem; font-size: 1.12rem; font-weight: 600; text-overflow: ellipsis; white-space: nowrap; }
.artist, .context { margin: 0; color: #d4bddf; font-size: 0.77rem; }
.context { display: flex; align-items: center; gap: 0.3rem; margin-top: 0.55rem; color: #e4d8ed; font-size: 0.64rem; letter-spacing: 0.04em; }
.context-marker { color: #75f3ee; font-size: 0.8rem; }
.context-separator { color: #617387; }

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
.progress-track { height: 0.18rem; overflow: hidden; border-radius: 99px; background: rgba(255, 255, 255, 0.15); }
.progress-track span { display: block; width: 29%; height: 100%; border-radius: inherit; background: linear-gradient(90deg, #6ef2eb, #ff69bd, #ffe475); transition: width 0.2s ease; }
.progress-track span.is-playing { width: 55%; animation: progress 4s linear infinite alternate; }
.time-row { margin-top: 0.42rem; color: #687c93; }

.controls { justify-content: center; gap: 0.8rem; margin-top: 1rem; }
.control-button { display: grid; place-items: center; border: 0; cursor: pointer; color: #dce9f5; background: transparent; transition: color 0.2s ease, transform 0.2s ease, background 0.2s ease; }
.control-button:hover { color: #ffb2da; transform: translateY(-1px); }
.control-button:focus-visible { outline: 2px solid #78f1ec; outline-offset: 3px; }
.control-button--play { width: 2.8rem; height: 2.8rem; border-radius: 50%; color: #281040; background: linear-gradient(145deg, #ffe36e, #ff9ccf); box-shadow: 0 0.3rem 1rem rgba(255, 112, 190, 0.36); }
.control-button--play:hover { color: #170427; background: #fff09c; }
.control-button--skip { order: 2; font-size: 1.35rem; }
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
@keyframes progress { from { width: 43%; } to { width: 66%; } }
@keyframes equalize { to { height: var(--peak-height); opacity: 1; } }

@media (prefers-reduced-motion: no-preference) { .artwork { animation: record-spin 15s linear infinite; } }
@keyframes record-spin { to { transform: rotate(360deg); } }

@media (max-width: 38rem) {
  .radio-panel { width: 100%; }
}
</style>

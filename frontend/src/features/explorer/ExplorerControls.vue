<script setup lang="ts">
import type { SimulationState } from '@/contracts/satellite'

const props = defineProps<{
  isPlaying: boolean
  speed: SimulationState['speed']
  showOrbitPath: boolean
}>()

const emit = defineEmits<{
  (event: 'toggle-play'): void
  (event: 'set-speed', speed: SimulationState['speed']): void
  (event: 'toggle-orbit-path'): void
}>()

const speeds: SimulationState['speed'][] = [1, 10, 60]
</script>

<template>
  <section class="explorer-controls" aria-label="Simulation controls">
    <div class="control-heading">
      <span class="eyebrow">MISSION CONTROL</span>
      <span class="target-count">01 TARGET ONLINE</span>
    </div>

    <div class="control-row">
      <button
        class="play-button"
        type="button"
        :aria-label="props.isPlaying ? 'Pause simulation' : 'Play simulation'"
        @click="emit('toggle-play')"
      >
        <span aria-hidden="true">{{ props.isPlaying ? 'Ⅱ' : '▶' }}</span>
      </button>

      <div class="speed-picker" role="group" aria-label="Simulation speed">
        <button
          v-for="value in speeds"
          :key="value"
          class="speed-button"
          :class="{ selected: props.speed === value }"
          type="button"
          :aria-label="`Set simulation speed to ${value}x`"
          :aria-pressed="props.speed === value"
          @click="emit('set-speed', value)"
        >
          {{ value }}x
        </button>
      </div>

      <button
        class="orbit-button"
        type="button"
        :aria-label="props.showOrbitPath ? 'Hide orbit path' : 'Show orbit path'"
        :aria-pressed="props.showOrbitPath"
        @click="emit('toggle-orbit-path')"
      >
        <span class="orbit-icon" aria-hidden="true" />
        <span>{{ props.showOrbitPath ? 'Orbit on' : 'Orbit off' }}</span>
      </button>
    </div>
  </section>
</template>

<style scoped>
.explorer-controls {
  border: 1px solid rgba(255, 135, 205, 0.26);
  border-radius: 14px;
  background: rgba(27, 13, 58, 0.84);
  box-shadow: 0 18px 48px rgba(0, 0, 0, 0.25);
  padding: 14px 16px 16px;
  backdrop-filter: blur(16px);
}

.control-heading,
.control-row {
  align-items: center;
  display: flex;
}

.control-heading {
  justify-content: space-between;
  margin-bottom: 13px;
}

.eyebrow {
  color: rgba(194, 245, 241, 0.74);
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 0.2em;
}

.target-count {
  color: #7ff4e9;
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 0.16em;
}

.control-row {
  gap: 8px;
}

button {
  border: 0;
  color: inherit;
  cursor: pointer;
  transition: background-color 160ms ease, border-color 160ms ease, color 160ms ease, transform 160ms ease;
}

button:focus-visible {
  outline: 2px solid #75f1ec;
  outline-offset: 2px;
}

button:active {
  transform: translateY(1px);
}

.play-button {
  align-items: center;
  background: linear-gradient(145deg, #ff83c9, #ffe36e);
  border-radius: 50%;
  color: #2c0c45;
  display: inline-flex;
  font-size: 13px;
  height: 32px;
  justify-content: center;
  line-height: 1;
  padding: 0 0 1px;
  width: 32px;
}

.play-button:hover {
  background: #fff09b;
}

.speed-picker {
  background: rgba(255, 255, 255, 0.045);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 8px;
  display: inline-flex;
  padding: 2px;
}

.speed-button {
  background: transparent;
  border-radius: 6px;
  color: rgba(239, 222, 248, 0.72);
  font-size: 10px;
  font-weight: 700;
  min-width: 31px;
  padding: 6px 5px;
}

.speed-button:hover,
.speed-button.selected {
  background: rgba(255, 111, 195, 0.22);
  color: #fff4fb;
}

.orbit-button {
  align-items: center;
  background: rgba(255, 255, 255, 0.045);
  border: 1px solid rgba(255, 255, 255, 0.07);
  border-radius: 8px;
  color: rgba(235, 224, 248, 0.8);
  display: inline-flex;
  font-size: 10px;
  gap: 7px;
  margin-left: auto;
  padding: 7px 9px;
}

.orbit-button:hover {
  background: rgba(117, 241, 236, 0.14);
  color: #eafffd;
}

.orbit-icon {
  border: 1px solid currentColor;
  border-radius: 50%;
  display: inline-block;
  height: 12px;
  position: relative;
  transform: rotate(-28deg);
  width: 18px;
}

.orbit-icon::after {
  background: currentColor;
  border-radius: 50%;
  content: '';
  height: 3px;
  position: absolute;
  right: -1px;
  top: -2px;
  width: 3px;
}

@media (max-width: 540px) {
  .explorer-controls {
    padding: 12px;
  }

  .orbit-button span:last-child {
    display: none;
  }
}
</style>

<script setup lang="ts">
import type { SatelliteCatalogEntry } from '@/contracts/satellite'

defineProps<{
  satellite: SatelliteCatalogEntry
}>()

const emit = defineEmits<{
  (event: 'focus'): void
}>()
</script>

<template>
  <section class="satellite-panel" aria-label="Selected satellite">
    <div class="panel-rule" aria-hidden="true" />
    <div class="panel-kicker">
      <span class="signal-mark" aria-hidden="true" />
      TRACKING TARGET
    </div>
    <div class="satellite-title-row">
      <div>
        <h1>{{ satellite.name }}</h1>
        <p>{{ satellite.description }}</p>
      </div>
      <span class="target-badge">ISS</span>
    </div>
    <dl class="telemetry-grid">
      <div>
        <dt>NORAD ID</dt>
        <dd>{{ satellite.noradId }}</dd>
      </div>
      <div>
        <dt>ORBIT CLASS</dt>
        <dd>LEO · 51.6°</dd>
      </div>
      <div>
        <dt>STATUS</dt>
        <dd class="status-value"><span class="status-light" />SIMULATED</dd>
      </div>
    </dl>
    <button class="focus-button" type="button" aria-label="Focus on ISS" @click="emit('focus')">
      <span aria-hidden="true">◎</span>
      Focus camera
    </button>
  </section>
</template>

<style scoped>
.satellite-panel {
  background: linear-gradient(145deg, rgba(40, 15, 65, 0.92), rgba(10, 20, 53, 0.86));
  border: 1px solid rgba(117, 239, 234, 0.25);
  border-radius: 18px;
  box-shadow: 0 24px 70px rgba(0, 0, 0, 0.3), inset 0 1px rgba(255, 255, 255, 0.1);
  max-width: 375px;
  overflow: hidden;
  padding: 18px;
  position: relative;
}

.panel-rule {
  background: linear-gradient(90deg, #ff75c4, #75f1ec, rgba(117, 241, 236, 0));
  height: 1px;
  left: 18px;
  opacity: 0.85;
  position: absolute;
  right: 18px;
  top: 0;
}

.panel-kicker {
  align-items: center;
  color: rgba(187, 242, 239, 0.76);
  display: flex;
  font-size: 9px;
  font-weight: 700;
  gap: 8px;
  letter-spacing: 0.18em;
  margin-bottom: 13px;
}

.signal-mark {
  border: 1px solid #75f1ec;
  border-radius: 50%;
  box-shadow: inset 0 0 0 2px rgba(117, 241, 236, 0.12), 0 0 0.7rem rgba(117, 241, 236, 0.28);
  display: inline-block;
  height: 10px;
  position: relative;
  width: 10px;
}

.signal-mark::after {
  background: #ff78c7;
  border-radius: 50%;
  content: '';
  height: 3px;
  left: 3px;
  position: absolute;
  top: 3px;
  width: 3px;
}

.satellite-title-row {
  align-items: flex-start;
  display: flex;
  gap: 14px;
  justify-content: space-between;
}

h1 {
  color: #fff5fc;
  font-size: 20px;
  font-weight: 500;
  letter-spacing: -0.025em;
  line-height: 1.15;
  margin: 0;
}

p {
  color: rgba(224, 208, 239, 0.76);
  font-size: 11px;
  line-height: 1.5;
  margin: 6px 0 0;
}

.target-badge {
  border: 1px solid rgba(255, 124, 199, 0.62);
  border-radius: 5px;
  color: #ffb7df;
  font-size: 9px;
  font-weight: 800;
  letter-spacing: 0.14em;
  padding: 4px 6px;
}

.telemetry-grid {
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  display: grid;
  gap: 11px;
  grid-template-columns: repeat(3, 1fr);
  margin: 17px 0 14px;
  padding: 13px 0;
}

dl,
dt,
dd {
  margin: 0;
}

dt {
  color: rgba(193, 228, 239, 0.58);
  font-size: 8px;
  font-weight: 700;
  letter-spacing: 0.12em;
  margin-bottom: 5px;
}

dd {
  color: #e6f5f3;
  font-size: 11px;
  white-space: nowrap;
}

.status-value {
  align-items: center;
  color: #a7f5c9;
  display: inline-flex;
  gap: 5px;
}

.status-light {
  background: #77d7a7;
  border-radius: 50%;
  box-shadow: 0 0 8px rgba(119, 215, 167, 0.8);
  display: inline-block;
  height: 5px;
  width: 5px;
}

.focus-button {
  align-items: center;
  background: linear-gradient(90deg, rgba(255, 110, 192, 0.16), rgba(109, 240, 235, 0.14));
  border: 1px solid rgba(117, 241, 236, 0.35);
  border-radius: 8px;
  color: #e7fffd;
  cursor: pointer;
  display: inline-flex;
  font-size: 11px;
  gap: 7px;
  padding: 8px 11px;
}

.focus-button:hover {
  background: rgba(255, 118, 197, 0.28);
}

.focus-button:focus-visible {
  outline: 2px solid #75f1ec;
  outline-offset: 2px;
}

@media (max-width: 540px) {
  .satellite-panel {
    max-width: none;
  }
}
</style>

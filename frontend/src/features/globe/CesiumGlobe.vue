<script setup lang="ts">
import * as Cesium from 'cesium'
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import type { OrbitPosition, SatelliteCatalogEntry } from '@/contracts/satellite'
import { DemoOrbitPositionSource } from './DemoOrbitPositionSource'
import { InterpolatedOrbitPositionSource } from './InterpolatedOrbitPositionSource'
import {
  applyAlwaysDaylightGlobeOptions,
  applyCountryScaleZoomLimit,
  createGoogleSatelliteWithLabelsBaseLayer,
  createWorldTerrain,
} from './GlobeLayers'

const props = withDefaults(defineProps<{
  satellite: SatelliteCatalogEntry
  isPlaying?: boolean
  speed?: 1 | 10 | 60
  showOrbitPath?: boolean
}>(), {
  isPlaying: true,
  speed: 1,
  showOrbitPath: true,
})

const emit = defineEmits<{
  (event: 'satellite-selected', satellite: SatelliteCatalogEntry): void
  (event: 'position-updated', position: OrbitPosition): void
}>()

const cesiumHost = ref<HTMLElement | null>(null)
const isFallback = ref(false)
const isSatelliteImageryUnavailable = ref(false)

let viewer: Cesium.Viewer | undefined
let satelliteEntity: Cesium.Entity | undefined
let orbitEntity: Cesium.Entity | undefined
function createOrbitSource(satelliteId: string): InterpolatedOrbitPositionSource {
  const source = new DemoOrbitPositionSource(satelliteId)
  return new InterpolatedOrbitPositionSource(source, {
    sampleIntervalSeconds: 5,
    cacheWindowSeconds: source.pathDurationSeconds,
  })
}

const ORBIT_PATH_UPDATE_INTERVAL_MS = 200

let orbitSource = createOrbitSource(props.satellite.id)
let simulationTime = new Date('2026-08-23T00:00:00.000Z')
let animationFrame: number | undefined
let lastFrameTime: number | undefined
let lastPositionEmitAt: number | undefined
let lastOrbitPathUpdateAt: number | undefined

function toCartesian(position: OrbitPosition): Cesium.Cartesian3 | undefined {
  if (!Cesium.Cartesian3?.fromDegrees) return undefined
  return Cesium.Cartesian3.fromDegrees(position.longitudeDeg, position.latitudeDeg, position.altitudeKm * 1000)
}

function colorFromCss(color: string): Cesium.Color | undefined {
  if (!Cesium.Color?.fromCssColorString) return undefined
  return Cesium.Color.fromCssColorString(color)
}

function syncSatellitePosition(position: OrbitPosition): void {
  if (!satelliteEntity) return
  const cartesianPosition = toCartesian(position)
  // Cesium accepts a Cartesian3 here and wraps it as a constant property at
  // runtime; the public Entity type models the more general property shape.
  if (cartesianPosition) satelliteEntity.position = cartesianPosition as never
}

function emitCurrentPosition(position: OrbitPosition, force = false): void {
  const now = Date.now()
  if (!force && lastPositionEmitAt !== undefined && now - lastPositionEmitAt < 1_000) return
  lastPositionEmitAt = now
  emit('position-updated', position)
}

function syncOrbitPath(force = false): void {
  if (!viewer || !orbitEntity) return
  const now = Date.now()
  if (!force && lastOrbitPathUpdateAt !== undefined && now - lastOrbitPathUpdateAt < ORBIT_PATH_UPDATE_INTERVAL_MS) return
  lastOrbitPathUpdateAt = now
  const positions = props.showOrbitPath
    ? orbitSource.getPath?.(simulationTime, 96)?.map(toCartesian).filter((position): position is Cesium.Cartesian3 => Boolean(position))
    : undefined

  // Keep Cesium's graphics objects imperative and outside Vue's reactive
  // graph. The object literal is the shape accepted by EntityCollection.add.
  orbitEntity.polyline = (props.showOrbitPath && positions?.length
    ? {
        positions,
        width: 1.5,
        material: colorFromCss(props.satellite.accentColor),
        clampToGround: false,
      }
    : undefined) as never
  orbitEntity.show = props.showOrbitPath
}

function addEntities(): void {
  if (!viewer || !Cesium.Cartesian3?.fromDegrees || !viewer.entities?.add) return

  const position = toCartesian(orbitSource.getPosition(simulationTime))
  const color = colorFromCss(props.satellite.accentColor)
  satelliteEntity = viewer.entities.add({
    id: props.satellite.id,
    name: props.satellite.name,
    position,
    point: {
      pixelSize: 10,
      color,
      outlineColor: Cesium.Color?.WHITE,
      outlineWidth: 2,
      heightReference: Cesium.HeightReference?.NONE,
    },
  })

  orbitEntity = viewer.entities.add({
    id: `${props.satellite.id}-orbit`,
    name: `${props.satellite.name} orbit`,
    show: props.showOrbitPath,
  })
  syncOrbitPath(true)
}

function handlePick(movement: { position: unknown }): void {
  if (!viewer || !satelliteEntity) return
  const picked = viewer.scene?.pick?.(movement.position as Cesium.Cartesian2)
  const pickedId = picked?.id
  if (pickedId === satelliteEntity || pickedId?.id === props.satellite.id || pickedId === props.satellite.id) {
    emit('satellite-selected', props.satellite)
  }
}

function startAnimation(): void {
  if (animationFrame !== undefined || typeof window === 'undefined' || !window.requestAnimationFrame) return

  const tick = (frameTime: number): void => {
    animationFrame = window.requestAnimationFrame(tick)
    if (lastFrameTime === undefined) lastFrameTime = frameTime
    const deltaSeconds = Math.min(1, Math.max(0, frameTime - lastFrameTime) / 1000)
    lastFrameTime = frameTime

    if (props.isPlaying) {
      simulationTime = new Date(simulationTime.getTime() + deltaSeconds * props.speed * 1000)
      const position = orbitSource.getPosition(simulationTime)
      syncSatellitePosition(position)
      syncOrbitPath()
      emitCurrentPosition(position)
    } else {
      emitCurrentPosition(orbitSource.getPosition(simulationTime))
    }
  }

  animationFrame = window.requestAnimationFrame(tick)
}

function stopAnimation(): void {
  if (animationFrame !== undefined && typeof window !== 'undefined' && window.cancelAnimationFrame) {
    window.cancelAnimationFrame(animationFrame)
  }
  animationFrame = undefined
  lastFrameTime = undefined
}

function focusSatellite(): void {
  if (!viewer || !satelliteEntity) return
  if (typeof viewer.flyTo === 'function') {
    void viewer.flyTo(satelliteEntity, { duration: 1.2 })
    return
  }

  const position = toCartesian(orbitSource.getPosition(simulationTime))
  if (position && typeof viewer.camera?.flyTo === 'function') {
    viewer.camera.flyTo({ destination: position })
  }
}

function initializeCesium(): void {
  // Give the application an initial position even when WebGL or a Cesium ion
  // token is unavailable. Subsequent samples are rate-limited to wall-clock
  // once per second, independently of simulation speed.
  emitCurrentPosition(orbitSource.getPosition(simulationTime), true)
  if (!cesiumHost.value || typeof Cesium.Viewer !== 'function') {
    isFallback.value = true
    return
  }

  try {
    const cesiumIonToken = import.meta.env.VITE_CESIUM_ION_TOKEN
    const baseLayer = createGoogleSatelliteWithLabelsBaseLayer(cesiumIonToken)
    const terrain = createWorldTerrain(cesiumIonToken)
    viewer = new Cesium.Viewer(cesiumHost.value, {
      animation: false,
      baseLayerPicker: false,
      fullscreenButton: false,
      geocoder: false,
      homeButton: false,
      infoBox: false,
      navigationHelpButton: false,
      sceneModePicker: false,
      selectionIndicator: false,
      timeline: false,
      shouldAnimate: false,
      baseLayer,
      terrain: terrain || undefined,
    } as never)

    if (!viewer) {
      isFallback.value = true
      return
    }

    addEntities()
    applyCountryScaleZoomLimit(viewer)
    applyAlwaysDaylightGlobeOptions(viewer)
    if (!cesiumIonToken) {
      isSatelliteImageryUnavailable.value = true
    }
    viewer.screenSpaceEventHandler?.setInputAction?.((movement: { position: unknown }) => handlePick(movement), Cesium.ScreenSpaceEventType?.LEFT_CLICK)
    startAnimation()
  } catch {
    isFallback.value = true
    viewer = undefined
  }
}

watch(() => props.showOrbitPath, () => syncOrbitPath(true))
watch(() => props.satellite, (satellite) => {
  orbitSource = createOrbitSource(satellite.id)
  if (satelliteEntity) {
    satelliteEntity.id = satellite.id
    satelliteEntity.name = satellite.name
  }
  const position = orbitSource.getPosition(simulationTime)
  syncSatellitePosition(position)
  syncOrbitPath(true)
  emitCurrentPosition(position, true)
})

onMounted(initializeCesium)

onBeforeUnmount(() => {
  stopAnimation()
  const destroyed = viewer && typeof viewer.isDestroyed === 'function' ? viewer.isDestroyed() : false
  if (viewer && typeof viewer.destroy === 'function' && !destroyed) viewer.destroy()
  viewer = undefined
  satelliteEntity = undefined
  orbitEntity = undefined
})

defineExpose({ focusSatellite })
</script>

<template>
  <section class="cesium-globe" aria-label="ISS globe simulation">
    <div ref="cesiumHost" class="cesium-globe__canvas" aria-hidden="true" />
    <div v-if="isFallback" class="cesium-globe__fallback" role="img" aria-label="ISS simulation fallback">
      WebGL globe unavailable — ISS SIMULATION remains available in this view.
    </div>
    <div v-else-if="isSatelliteImageryUnavailable" class="cesium-globe__fallback cesium-globe__fallback--setup" role="status">
      Satellite imagery requires a Cesium ion token. Add VITE_CESIUM_ION_TOKEN to frontend/.env.local and restart Vite.
    </div>
  </section>
</template>

<style scoped>
.cesium-globe {
  position: relative;
  min-height: 480px;
  height: 100%;
  width: 100%;
  overflow: hidden;
  background: radial-gradient(circle at 50% 42%, #12304b 0%, #07131f 42%, #02070d 100%);
  color: #dff3ff;
}

.cesium-globe__canvas {
  position: absolute;
  inset: 0;
}

.cesium-globe__fallback {
  position: absolute;
  inset: 50% 1.5rem auto;
  transform: translateY(-50%);
  padding: 1rem;
  border: 1px solid rgba(130, 202, 255, 0.24);
  border-radius: 0.8rem;
  background: rgba(2, 12, 21, 0.8);
  color: rgba(223, 243, 255, 0.72);
  text-align: center;
  font: 0.72rem/1.5 ui-monospace, SFMono-Regular, Menlo, monospace;
}

.cesium-globe__fallback--setup {
  inset: auto 1.5rem 1.5rem;
  transform: none;
}

</style>

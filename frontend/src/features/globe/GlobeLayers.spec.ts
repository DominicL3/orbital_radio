import { describe, expect, it, vi } from 'vitest'

const cesiumMocks = vi.hoisted(() => {
  const provider = { kind: 'google-satellite-provider' }
  return {
    provider,
    Ion: { defaultAccessToken: '' },
    IonImageryProvider: { fromAssetId: vi.fn(() => Promise.resolve(provider)) },
    ImageryLayer: { fromProviderAsync: vi.fn(() => ({ kind: 'google-satellite-layer' })) },
    Terrain: { fromWorldTerrain: vi.fn(() => ({ kind: 'world-terrain' })) },
  }
})

vi.mock('cesium', () => cesiumMocks)

import {
  applyAlwaysDaylightGlobeOptions,
  applyCountryScaleZoomLimit,
  createGoogleSatelliteWithLabelsBaseLayer,
  createWorldTerrain,
} from './GlobeLayers'

describe('createGoogleSatelliteWithLabelsBaseLayer', () => {
  it('does not request imagery when no Cesium ion token is configured', () => {
    expect(createGoogleSatelliteWithLabelsBaseLayer()).toBe(false)
    expect(cesiumMocks.IonImageryProvider.fromAssetId).not.toHaveBeenCalled()
  })

  it('uses Cesium ion Google Satellite with Labels imagery when a token is configured', () => {
    const baseLayer = createGoogleSatelliteWithLabelsBaseLayer('test-token')

    expect(cesiumMocks.Ion.defaultAccessToken).toBe('test-token')
    expect(cesiumMocks.IonImageryProvider.fromAssetId).toHaveBeenCalledWith(3830183)
    expect(cesiumMocks.ImageryLayer.fromProviderAsync).toHaveBeenCalledWith(
      expect.any(Promise),
    )
    expect(baseLayer).toEqual({ kind: 'google-satellite-layer' })
  })
})

describe('createWorldTerrain', () => {
  it('requests terrain with vertex normals when a token is configured', () => {
    const terrain = createWorldTerrain('test-token')

    expect(cesiumMocks.Ion.defaultAccessToken).toBe('test-token')
    expect(cesiumMocks.Terrain.fromWorldTerrain).toHaveBeenCalledWith({
      requestVertexNormals: true,
    })
    expect(terrain).toEqual({ kind: 'world-terrain' })
  })
})

describe('applyCountryScaleZoomLimit', () => {
  it('prevents the camera from getting closer than 100 km', () => {
    const controller = { minimumZoomDistance: 1 }

    applyCountryScaleZoomLimit({
      scene: { screenSpaceCameraController: controller },
    })

    expect(controller.minimumZoomDistance).toBe(100_000)
  })
})

describe('applyAlwaysDaylightGlobeOptions', () => {
  it('disables sun-position lighting so every country remains visible', () => {
    const globe = { enableLighting: true }

    applyAlwaysDaylightGlobeOptions({ scene: { globe } })

    expect(globe.enableLighting).toBe(false)
  })
})

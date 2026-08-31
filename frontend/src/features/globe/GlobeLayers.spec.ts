import { describe, expect, it, vi } from 'vitest'

const cesiumMocks = vi.hoisted(() => {
  const provider = { kind: 'sentinel-provider' }
  return {
    provider,
    Ion: { defaultAccessToken: '' },
    IonImageryProvider: { fromAssetId: vi.fn(() => Promise.resolve(provider)) },
    ImageryLayer: { fromProviderAsync: vi.fn(() => ({ kind: 'sentinel-layer' })) },
    Terrain: { fromWorldTerrain: vi.fn(() => ({ kind: 'world-terrain' })) },
  }
})

vi.mock('cesium', () => cesiumMocks)

import { applyCountryScaleZoomLimit, createSentinel2BaseLayer, createWorldTerrain } from './GlobeLayers'

describe('createSentinel2BaseLayer', () => {
  it('does not request imagery when no Cesium ion token is configured', () => {
    expect(createSentinel2BaseLayer()).toBe(false)
    expect(cesiumMocks.IonImageryProvider.fromAssetId).not.toHaveBeenCalled()
  })

  it('uses Cesium ion Sentinel-2 imagery when a token is configured', () => {
    const baseLayer = createSentinel2BaseLayer('test-token')

    expect(cesiumMocks.Ion.defaultAccessToken).toBe('test-token')
    expect(cesiumMocks.IonImageryProvider.fromAssetId).toHaveBeenCalledWith(3954)
    expect(cesiumMocks.ImageryLayer.fromProviderAsync).toHaveBeenCalledWith(
      expect.any(Promise),
    )
    expect(baseLayer).toEqual({ kind: 'sentinel-layer' })
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

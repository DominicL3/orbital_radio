import { describe, expect, it } from 'vitest'
import type { OrbitPosition, OrbitPositionSource } from '@/contracts/satellite'
import { InterpolatedOrbitPositionSource } from './InterpolatedOrbitPositionSource'

class CountingPositionSource implements OrbitPositionSource {
  readonly satelliteId = 'test-satellite'
  readonly requestedAt: number[] = []

  getPosition(at: Date): OrbitPosition {
    const seconds = at.getTime() / 1_000
    this.requestedAt.push(seconds)
    return {
      timestamp: new Date(at),
      latitudeDeg: seconds,
      longitudeDeg: seconds,
      altitudeKm: 400 + seconds,
    }
  }
}

describe('InterpolatedOrbitPositionSource', () => {
  it('interpolates marker positions from a rolling sample window', () => {
    const source = new CountingPositionSource()
    const cached = new InterpolatedOrbitPositionSource(source, {
      sampleIntervalSeconds: 10,
      cacheWindowSeconds: 30,
    })

    const position = cached.getPosition(new Date(5_000))

    expect(position).toMatchObject({ latitudeDeg: 5, longitudeDeg: 5, altitudeKm: 405 })
    expect(source.requestedAt).toEqual([0, 10, 20, 30, 40])

    cached.getPosition(new Date(15_000))
    expect(source.requestedAt).toEqual([0, 10, 20, 30, 40, 50])
  })

  it('serves the visible path from the same cache instead of resampling the source', () => {
    const source = new CountingPositionSource()
    const cached = new InterpolatedOrbitPositionSource(source, {
      sampleIntervalSeconds: 10,
      cacheWindowSeconds: 30,
    })

    const path = cached.getPath(new Date(0), 4)

    expect(path.map((position) => position.latitudeDeg)).toEqual([0, 10, 20, 30])
    expect(source.requestedAt).toEqual([0, 10, 20, 30])
  })

  it('interpolates across the anti-meridian along the shortest route', () => {
    const source: OrbitPositionSource = {
      satelliteId: 'anti-meridian',
      getPosition(at) {
        return {
          timestamp: new Date(at),
          latitudeDeg: 0,
          longitudeDeg: at.getTime() === 0 ? 179 : -179,
          altitudeKm: 400,
        }
      },
    }
    const cached = new InterpolatedOrbitPositionSource(source, {
      sampleIntervalSeconds: 10,
      cacheWindowSeconds: 10,
    })

    expect(cached.getPosition(new Date(5_000)).longitudeDeg).toBeCloseTo(-180)
  })
})

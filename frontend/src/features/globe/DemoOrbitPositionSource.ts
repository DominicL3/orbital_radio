import type { OrbitPosition, OrbitPositionSource } from '@/contracts/satellite'

/**
 * A small, deterministic ISS-like orbit used while the application is not
 * connected to a TLE feed.  The source intentionally has the same shape as a
 * future satellite.js-backed source, so Cesium and the UI do not need to know
 * where a position came from.
 */
export class DemoOrbitPositionSource implements OrbitPositionSource {
  readonly satelliteId: string

  private readonly epoch: number
  private readonly periodSeconds: number
  private readonly inclinationRadians: number
  private readonly altitudeKm: number

  constructor(
    satelliteId = 'iss',
    options: {
      epoch?: Date
      periodSeconds?: number
      inclinationDeg?: number
      altitudeKm?: number
    } = {},
  ) {
    this.satelliteId = satelliteId
    this.epoch = (options.epoch ?? new Date('2026-08-23T00:00:00.000Z')).getTime()
    this.periodSeconds = options.periodSeconds ?? 92.68 * 60
    this.inclinationRadians = ((options.inclinationDeg ?? 51.6) * Math.PI) / 180
    this.altitudeKm = options.altitudeKm ?? 408
  }

  getPosition(at: Date): OrbitPosition {
    const elapsedSeconds = (at.getTime() - this.epoch) / 1000
    const phase = (2 * Math.PI * elapsedSeconds) / this.periodSeconds

    // A simple inclined circular orbit. Accounting for Earth rotation gives
    // the marker a familiar west/east-moving ground track instead of merely
    // drawing a circle around a fixed longitude.
    const latitudeDeg = (Math.asin(Math.sin(this.inclinationRadians) * Math.sin(phase)) * 180) / Math.PI
    const orbitalLongitudeDeg = (phase * 180) / Math.PI
    const earthRotationDeg = (elapsedSeconds / 86164.0905) * 360
    const longitudeDeg = wrapDegrees(orbitalLongitudeDeg - earthRotationDeg - 25)

    return {
      timestamp: new Date(at.getTime()),
      longitudeDeg,
      latitudeDeg,
      // A very small variation keeps the marker from feeling mathematically
      // frozen while keeping it within a plausible ISS altitude band.
      altitudeKm: this.altitudeKm + Math.sin(phase * 2) * 3,
    }
  }

  getPath(at: Date, samples = 96): OrbitPosition[] {
    const count = Math.max(2, Math.floor(samples))
    const stepSeconds = this.periodSeconds / (count - 1)

    return Array.from({ length: count }, (_, index) =>
      this.getPosition(new Date(at.getTime() + index * stepSeconds * 1000)),
    )
  }
}

function wrapDegrees(degrees: number): number {
  return ((degrees + 180) % 360 + 360) % 360 - 180
}


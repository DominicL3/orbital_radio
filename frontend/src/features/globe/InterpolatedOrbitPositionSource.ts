import type { OrbitPosition, OrbitPositionSource } from '@/contracts/satellite'

export interface InterpolatedOrbitPositionSourceOptions {
  /** Simulation-time spacing between the source samples kept in memory. */
  sampleIntervalSeconds?: number
  /** Simulation-time horizon retained ahead of the current position. */
  cacheWindowSeconds: number
}

/**
 * Keeps a small rolling simulation-time buffer around an orbit source.
 *
 * The wrapped source is sampled at a fixed cadence. Consumers can then ask
 * for arbitrary timestamps and receive an interpolated position, which keeps
 * the marker smooth without evaluating a future TLE/SGP4 source every frame.
 */
export class InterpolatedOrbitPositionSource implements OrbitPositionSource {
  readonly satelliteId: string

  private readonly sampleIntervalMs: number
  private readonly cacheWindowMs: number
  private samples: OrbitPosition[] = []

  constructor(
    private readonly source: OrbitPositionSource,
    options: InterpolatedOrbitPositionSourceOptions,
  ) {
    if (!Number.isFinite(options.cacheWindowSeconds) || options.cacheWindowSeconds <= 0) {
      throw new RangeError('cacheWindowSeconds must be a positive number')
    }

    const sampleIntervalSeconds = options.sampleIntervalSeconds ?? 5
    if (!Number.isFinite(sampleIntervalSeconds) || sampleIntervalSeconds <= 0) {
      throw new RangeError('sampleIntervalSeconds must be a positive number')
    }

    this.satelliteId = source.satelliteId
    this.sampleIntervalMs = sampleIntervalSeconds * 1_000
    this.cacheWindowMs = options.cacheWindowSeconds * 1_000
  }

  getPosition(at: Date): OrbitPosition {
    this.prepareWindow(at)
    return this.interpolate(at)
  }

  getPath(at: Date, samples = 96): OrbitPosition[] {
    const count = Math.max(2, Math.floor(samples))
    this.prepareWindow(at)
    const stepMs = this.cacheWindowMs / (count - 1)

    return Array.from({ length: count }, (_, index) =>
      this.interpolate(new Date(at.getTime() + index * stepMs)),
    )
  }

  private prepareWindow(at: Date): void {
    const requestedAt = at.getTime()
    const firstSampleAt = this.floorToSample(requestedAt)
    const lastRequiredAt = this.ceilToSample(requestedAt + this.cacheWindowMs)

    if (!this.samples.length || firstSampleAt < this.samples[0]!.timestamp.getTime()) {
      this.samples = []
      this.appendSamples(firstSampleAt, lastRequiredAt)
      return
    }

    const currentLastAt = this.samples[this.samples.length - 1]!.timestamp.getTime()
    if (currentLastAt < lastRequiredAt) this.appendSamples(currentLastAt + this.sampleIntervalMs, lastRequiredAt)

    // Preserve the sample immediately before the requested time so the next
    // interpolation remains valid, while releasing samples left behind by the
    // simulated clock.
    while (this.samples.length > 2 && this.samples[1]!.timestamp.getTime() <= firstSampleAt) {
      this.samples.shift()
    }
  }

  private appendSamples(firstSampleAt: number, lastSampleAt: number): void {
    for (let sampleAt = firstSampleAt; sampleAt <= lastSampleAt; sampleAt += this.sampleIntervalMs) {
      this.samples.push(this.source.getPosition(new Date(sampleAt)))
    }
  }

  private interpolate(at: Date): OrbitPosition {
    const requestedAt = at.getTime()
    const lowerIndex = Math.max(0, Math.floor((requestedAt - this.samples[0]!.timestamp.getTime()) / this.sampleIntervalMs))
    const lower = this.samples[lowerIndex]!
    const upper = this.samples[Math.min(lowerIndex + 1, this.samples.length - 1)]!
    const lowerAt = lower.timestamp.getTime()
    const upperAt = upper.timestamp.getTime()
    const progress = upperAt === lowerAt ? 0 : (requestedAt - lowerAt) / (upperAt - lowerAt)

    return {
      timestamp: new Date(requestedAt),
      latitudeDeg: interpolateLinear(lower.latitudeDeg, upper.latitudeDeg, progress),
      longitudeDeg: interpolateLongitude(lower.longitudeDeg, upper.longitudeDeg, progress),
      altitudeKm: interpolateLinear(lower.altitudeKm, upper.altitudeKm, progress),
    }
  }

  private floorToSample(timestamp: number): number {
    return Math.floor(timestamp / this.sampleIntervalMs) * this.sampleIntervalMs
  }

  private ceilToSample(timestamp: number): number {
    return Math.ceil(timestamp / this.sampleIntervalMs) * this.sampleIntervalMs
  }
}

function interpolateLinear(from: number, to: number, progress: number): number {
  return from + (to - from) * progress
}

function interpolateLongitude(from: number, to: number, progress: number): number {
  const delta = ((to - from + 540) % 360) - 180
  return ((from + delta * progress + 540) % 360) - 180
}

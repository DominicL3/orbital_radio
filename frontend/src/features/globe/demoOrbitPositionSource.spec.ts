import { describe, expect, it } from 'vitest'
import { DemoOrbitPositionSource } from './DemoOrbitPositionSource'

describe('DemoOrbitPositionSource', () => {
  it('returns deterministic ISS-like low Earth orbit positions', () => {
    const source = new DemoOrbitPositionSource()
    const at = new Date('2026-08-23T00:00:00.000Z')
    expect(source.getPosition(at)).toEqual(source.getPosition(at))
    const position = source.getPosition(at)
    expect(position.altitudeKm).toBeGreaterThan(390)
    expect(position.altitudeKm).toBeLessThan(430)
    expect(position.latitudeDeg).toBeGreaterThanOrEqual(-52)
    expect(position.latitudeDeg).toBeLessThanOrEqual(52)
  })
})

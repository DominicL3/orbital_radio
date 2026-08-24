import { describe, expect, it } from 'vitest'
import { createSimulationController } from './simulation'

describe('simulation controller', () => {
  it('plays by default, toggles playback, and accepts supported speeds', () => {
    const controller = createSimulationController()
    expect(controller.state).toEqual({ isPlaying: true, speed: 1 })
    controller.toggle()
    controller.setSpeed(60)
    expect(controller.state).toEqual({ isPlaying: false, speed: 60 })
  })
})

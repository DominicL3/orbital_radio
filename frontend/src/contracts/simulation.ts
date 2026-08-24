import type { SimulationState } from './satellite'

export interface SimulationController {
  state: SimulationState
  toggle(): void
  setSpeed(speed: SimulationState['speed']): void
}

export function createSimulationController(initial: Partial<SimulationState> = {}): SimulationController {
  const state: SimulationState = { isPlaying: initial.isPlaying ?? true, speed: initial.speed ?? 1 }
  return {
    state,
    toggle: () => { state.isPlaying = !state.isPlaying },
    setSpeed: (speed) => { state.speed = speed },
  }
}

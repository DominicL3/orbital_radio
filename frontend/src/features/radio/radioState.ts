import { reactive } from 'vue'
import type { RadioState, RadioTrack } from '@/contracts/radio'

export interface RadioPlayer {
  state: RadioState
  toggle: () => void
  next: () => void
  previous: () => void
}

/**
 * Creates the local, fixture-backed player used by the radio panel.
 *
 * Keeping the player independent from the component means a future streaming
 * provider can replace this implementation without changing the presentation
 * contract. The MVP deliberately has no network or Spotify dependency.
 */
export function createRadioPlayer(tracks: readonly RadioTrack[]): RadioPlayer {
  let trackIndex = 0
  const state = reactive<RadioState>({
    status: tracks.length > 0 ? 'ready' : 'empty',
    isPlaying: false,
    track: tracks[0] ?? null,
  })

  const selectTrack = (nextIndex: number) => {
    if (tracks.length === 0) {
      state.status = 'empty'
      state.track = null
      state.isPlaying = false
      return
    }

    trackIndex = (nextIndex + tracks.length) % tracks.length
    state.status = 'ready'
    state.track = tracks[trackIndex]
    state.isPlaying = true
  }

  return {
    state,
    toggle: () => {
      if (state.status === 'ready' && state.track) {
        state.isPlaying = !state.isPlaying
      }
    },
    next: () => selectTrack(trackIndex + 1),
    previous: () => selectTrack(trackIndex - 1),
  }
}

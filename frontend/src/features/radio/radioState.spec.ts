import { describe, expect, it } from 'vitest'
import { createRadioPlayer } from './radioState'
import { mockRadioTracks } from '@/fixtures/radio'

describe('radio player state', () => {
  it('toggles playback and advances through fixture tracks', () => {
    const player = createRadioPlayer(mockRadioTracks)
    expect(player.state.track?.id).toBe('night-drive')
    player.toggle()
    player.next()
    expect(player.state.isPlaying).toBe(true)
    expect(player.state.track?.id).toBe('northern-signal')
  })
})

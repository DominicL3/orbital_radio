import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { RadioStation } from '@/contracts/radio'
import type { RadioApi } from './radioApi'
import type { AudioElementLike, RadioVolumeStorage } from './radioState'
import { createRadioPlayer } from './radioState'

class FakeAudio implements AudioElementLike {
  src = ''
  volume = 1
  preload = ''
  playCalls = 0
  pauseCalls = 0
  loadCalls = 0
  playResult: Promise<void> | void | (() => Promise<void> | void) = Promise.resolve()
  private listeners = new Map<string, Set<(event: Event) => void>>()

  play(): Promise<void> | void {
    this.playCalls += 1
    return typeof this.playResult === 'function' ? this.playResult() : this.playResult
  }

  pause(): void {
    this.pauseCalls += 1
  }

  load(): void {
    this.loadCalls += 1
  }

  removeAttribute(name: string): void {
    if (name === 'src') this.src = ''
  }

  addEventListener(type: string, listener: (event: Event) => void): void {
    const listeners = this.listeners.get(type) ?? new Set()
    listeners.add(listener)
    this.listeners.set(type, listeners)
  }

  removeEventListener(type: string, listener: (event: Event) => void): void {
    this.listeners.get(type)?.delete(listener)
  }

  emit(type: string): void {
    for (const listener of this.listeners.get(type) ?? []) listener(new Event(type))
  }
}

class FakeVolumeStorage implements RadioVolumeStorage {
  readonly values = new Map<string, string>()

  getItem(key: string): string | null {
    return this.values.get(key) ?? null
  }

  setItem(key: string, value: string): void {
    this.values.set(key, value)
  }
}

function station(stationUuid: string, countryCode = 'JP'): RadioStation {
  return {
    stationUuid,
    name: `Station ${stationUuid}`,
    countryCode,
    tags: ['rock', 'indie'],
    faviconUrl: null,
    homepageUrl: null,
    streamUrl: `https://streams.example.test/${stationUuid}.mp3`,
    codec: 'MP3',
    bitrate: 128,
  }
}

function apiFor(stations: Array<RadioStation | null | Error> = []): RadioApi & { selectStation: ReturnType<typeof vi.fn> } {
  const selectStation = vi.fn(async () => {
    const next = stations.shift()
    if (next instanceof Error) throw next
    return next ?? null
  })
  return {
    resolveCountry: vi.fn(),
    selectStation,
    reportFailedStation: vi.fn(async () => undefined),
  }
}

async function settle(): Promise<void> {
  for (let index = 0; index < 12; index += 1) await Promise.resolve()
}

describe('radio player', () => {
  beforeEach(() => vi.useFakeTimers())
  afterEach(() => vi.useRealTimers())

  it('defaults the output volume to 70 percent', () => {
    const audio = new FakeAudio()
    const player = createRadioPlayer({ api: apiFor(), audioFactory: () => audio, volumeStorage: null })

    expect(player.state.volume).toBe(70)
    expect(audio.volume).toBe(0.7)
  })

  it('loads a saved volume and persists clamped volume changes', () => {
    const audio = new FakeAudio()
    const storage = new FakeVolumeStorage()
    storage.setItem('orbital-radio.radio-volume.v1', '42')
    const player = createRadioPlayer({ api: apiFor(), audioFactory: () => audio, volumeStorage: storage })

    expect(player.state.volume).toBe(42)
    expect(audio.volume).toBe(0.42)

    player.setVolume(125)
    expect(player.state.volume).toBe(100)
    expect(audio.volume).toBe(1)
    expect(storage.getItem('orbital-radio.radio-volume.v1')).toBe('100')

    player.setVolume(-4)
    expect(player.state.volume).toBe(0)
    expect(audio.volume).toBe(0)
    expect(storage.getItem('orbital-radio.radio-volume.v1')).toBe('0')
  })

  it('uses the default volume when saved storage is malformed or unavailable', () => {
    const audio = new FakeAudio()
    const storage: RadioVolumeStorage = {
      getItem: () => 'loud',
      setItem: () => { throw new Error('storage unavailable') },
    }
    const player = createRadioPlayer({ api: apiFor(), audioFactory: () => audio, volumeStorage: storage })

    expect(player.state.volume).toBe(70)
    player.setVolume(Number.NaN)
    expect(player.state.volume).toBe(70)
    expect(audio.volume).toBe(0.7)
  })

  it('waits exactly 3 wall-clock seconds and does not select before the first gesture', async () => {
    const audio = new FakeAudio()
    const api = apiFor([station('jp-1')])
    const player = createRadioPlayer({ api, audioFactory: () => audio })

    player.observeCountry('jp')
    vi.advanceTimersByTime(2_999)
    expect(player.state.countryCode).toBeNull()
    expect(api.selectStation).not.toHaveBeenCalled()

    vi.advanceTimersByTime(1)
    expect(player.state.countryCode).toBe('JP')
    expect(player.state.status).toBe('waiting')
    expect(api.selectStation).not.toHaveBeenCalled()

    await player.toggle()
    expect(api.selectStation).toHaveBeenCalledOnce()
    expect(audio.playCalls).toBe(1)
    expect(player.state.status).toBe('playing')
  })

  it('resets the dwell timer when the candidate changes and ignores simulation speed', () => {
    const player = createRadioPlayer({ api: apiFor(), audioFactory: () => new FakeAudio(), dwellMs: 3_000 })

    player.observeCountry('JP')
    vi.advanceTimersByTime(2_000)
    player.observeCountry('NO')
    vi.advanceTimersByTime(1_000)
    expect(player.state.countryCode).toBeNull()
    vi.advanceTimersByTime(1_999)
    expect(player.state.countryCode).toBeNull()
    vi.advanceTimersByTime(1)
    expect(player.state.countryCode).toBe('NO')
  })

  it('cancels a pending country change over ocean or unknown coordinates', () => {
    const player = createRadioPlayer({ api: apiFor(), audioFactory: () => new FakeAudio() })

    player.observeCountry('JP')
    vi.advanceTimersByTime(2_000)
    player.observeCountry(null)
    vi.advanceTimersByTime(2_000)
    expect(player.state.countryCode).toBeNull()
    expect(player.state.candidateCountryCode).toBeNull()
  })

  it('detaches the live stream on pause and reconnects at the live edge on play', async () => {
    const audio = new FakeAudio()
    const api = apiFor([station('jp-1')])
    const player = createRadioPlayer({ api, audioFactory: () => audio })
    player.observeCountry('JP')
    vi.advanceTimersByTime(3_000)
    await player.toggle()

    expect(player.state.status).toBe('playing')
    expect(audio.src).toContain('jp-1')
    await player.toggle()
    expect(player.state.status).toBe('paused')
    expect(audio.src).toBe('')

    await player.toggle()
    expect(player.state.status).toBe('playing')
    expect(audio.playCalls).toBe(2)
    expect(audio.src).toContain('jp-1')
  })

  it('selects another station on Next, excludes the current UUID, and preserves play intent', async () => {
    const audio = new FakeAudio()
    const api = apiFor([station('jp-1'), station('jp-2')])
    const player = createRadioPlayer({ api, audioFactory: () => audio })
    player.observeCountry('JP')
    vi.advanceTimersByTime(3_000)
    await player.toggle()
    await player.next()

    expect(player.state.station?.stationUuid).toBe('jp-2')
    expect(player.state.status).toBe('playing')
    expect(audio.playCalls).toBe(2)
    expect(api.selectStation.mock.calls[1]?.[1]).toContain('jp-1')
  })

  it('keeps the selected volume while changing stations', async () => {
    const audio = new FakeAudio()
    const player = createRadioPlayer({ api: apiFor([station('jp-1'), station('jp-2')]), audioFactory: () => audio, volumeStorage: null })
    player.setVolume(36)
    player.observeCountry('JP')
    vi.advanceTimersByTime(3_000)
    await player.toggle()
    await player.next()

    expect(player.state.station?.stationUuid).toBe('jp-2')
    expect(player.state.volume).toBe(36)
    expect(audio.volume).toBe(0.36)
  })

  it('falls back after a rejected play without creating another audio element', async () => {
    const audio = new FakeAudio()
    const api = apiFor([station('jp-1'), station('jp-2'), station('jp-3'), station('jp-4')])
    let playCount = 0
    audio.playResult = () => {
      playCount += 1
      return playCount < 4 ? Promise.reject(new Error(`failure ${playCount}`)) : Promise.resolve()
    }
    const player = createRadioPlayer({ api, audioFactory: () => audio })
    player.observeCountry('JP')
    vi.advanceTimersByTime(3_000)
    await player.toggle()
    await settle()

    expect(player.state.status).toBe('playing')
    expect(player.state.station?.stationUuid).toBe('jp-4')
    expect(audio.playCalls).toBe(4)
    expect(api.selectStation).toHaveBeenCalledTimes(4)
  })

  it('reports an immediate media error and retries in the same country', async () => {
    const audio = new FakeAudio()
    const first = station('jp-1')
    const api = apiFor([first, station('jp-2')])
    const player = createRadioPlayer({ api, audioFactory: () => audio })
    player.observeCountry('JP')
    vi.advanceTimersByTime(3_000)
    await player.toggle()
    audio.emit('error')
    await settle()

    expect(api.reportFailedStation).toHaveBeenCalledWith('jp-1')
    expect(player.state.station?.stationUuid).toBe('jp-2')
    expect(player.state.status).toBe('playing')
  })

  it('waits five seconds before treating a stalled stream as failed', async () => {
    const audio = new FakeAudio()
    const api = apiFor([station('jp-1'), station('jp-2')])
    const player = createRadioPlayer({ api, audioFactory: () => audio })
    player.observeCountry('JP')
    vi.advanceTimersByTime(3_000)
    await player.toggle()
    audio.emit('stalled')
    vi.advanceTimersByTime(4_999)
    await settle()
    expect(player.state.station?.stationUuid).toBe('jp-1')
    expect(player.state.status).toBe('playing')

    vi.advanceTimersByTime(1)
    await settle()
    expect(player.state.station?.stationUuid).toBe('jp-2')
    expect(player.state.status).toBe('playing')
  })

  it('stops after three automatic retry attempts and exposes unavailable', async () => {
    const audio = new FakeAudio()
    const api = apiFor([station('jp-1'), station('jp-2'), station('jp-3'), station('jp-4')])
    audio.playResult = Promise.resolve()
    const player = createRadioPlayer({ api, audioFactory: () => audio })
    player.observeCountry('JP')
    vi.advanceTimersByTime(3_000)
    await player.toggle()
    audio.playResult = Promise.reject(new Error('stream unavailable'))
    audio.emit('error')
    await settle()

    expect(api.selectStation).toHaveBeenCalledTimes(4)
    expect(player.state.status).toBe('unavailable')
    expect(player.state.isPlaying).toBe(false)
  })

  it('shows unavailable when the backend returns 204/no station', async () => {
    const player = createRadioPlayer({ api: apiFor([null]), audioFactory: () => new FakeAudio() })
    player.observeCountry('JP')
    vi.advanceTimersByTime(3_000)
    await player.toggle()

    expect(player.state.status).toBe('unavailable')
    expect(player.state.isPlaying).toBe(false)
  })
})

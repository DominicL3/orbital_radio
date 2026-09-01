import { reactive } from 'vue'
import type { RadioState, RadioStation } from '@/contracts/radio'
import type { RadioApi } from './radioApi'

export interface AudioElementLike {
  src: string
  preload?: string
  play(): Promise<void> | void
  pause(): void
  load?(): void
  removeAttribute?(name: string): void
  addEventListener(type: string, listener: (event: Event) => void): void
  removeEventListener(type: string, listener: (event: Event) => void): void
}

export interface RadioPlayerOptions {
  api: RadioApi
  audioFactory?: () => AudioElementLike
  dwellMs?: number
  maxAutomaticRetries?: number
  recentStationLimit?: number
  failedStationLimit?: number
  failedStationTtlMs?: number
}

export interface RadioPlayer {
  readonly state: RadioState
  /** Feed the player the latest country resolved from the orbit position. */
  observeCountry(countryCode: string | null): void
  /** Toggle a user-requested live connection. */
  toggle(): Promise<void>
  /** Select another station for the committed country. */
  next(): Promise<void>
  /** Release timers, listeners, and the single page-lifetime audio element. */
  dispose(): void
  /** Exposed for deterministic tests and diagnostics, never for a second player. */
  getAudioElement(): AudioElementLike
}

const DEFAULT_DWELL_MS = 3_000
const DEFAULT_MAX_AUTOMATIC_RETRIES = 3
const DEFAULT_RECENT_STATION_LIMIT = 32
const DEFAULT_FAILED_STATION_LIMIT = 64
const DEFAULT_FAILED_STATION_TTL_MS = 10 * 60 * 1_000

/**
 * Own one live audio connection for the lifetime of the page. No station is
 * selected or played until a user asks to play, while country changes after a
 * successful first play can select and reconnect automatically.
 */
export function createRadioPlayer(options: RadioPlayerOptions): RadioPlayer {
  const {
    api,
    audioFactory = createBrowserAudio,
    dwellMs = DEFAULT_DWELL_MS,
    maxAutomaticRetries = DEFAULT_MAX_AUTOMATIC_RETRIES,
    recentStationLimit = DEFAULT_RECENT_STATION_LIMIT,
    failedStationLimit = DEFAULT_FAILED_STATION_LIMIT,
    failedStationTtlMs = DEFAULT_FAILED_STATION_TTL_MS,
  } = options

  const audio = audioFactory()
  audio.preload = 'none'
  const state = reactive<RadioState>({
    status: 'waiting',
    isPlaying: false,
    station: null,
    countryCode: null,
    candidateCountryCode: null,
    error: null,
  })

  let disposed = false
  let dwellTimer: ReturnType<typeof setTimeout> | undefined
  let stalledTimer: ReturnType<typeof setTimeout> | undefined
  let committedCountry: string | null = null
  let candidateCountry: string | null = null
  let desiredPlaying = false
  let hasUserStartedPlayback = false
  let selectionSequence = 0
  let sourceSequence = 0
  let retryCycleActive = false
  let retryCount = 0
  let suppressAudioEvents = false

  const recentStationUuids: string[] = []
  const failedStationUuids = new Map<string, number>()

  const onPlaying = () => {
    clearStalledTimer()
    if (suppressAudioEvents || disposed || !desiredPlaying) return
    state.isPlaying = true
    state.status = 'playing'
    state.error = null
  }
  const onPause = () => {
    if (suppressAudioEvents || disposed || !state.isPlaying) return
    state.isPlaying = false
    if (desiredPlaying) state.status = 'paused'
  }
  const onWaiting = () => {
    if (suppressAudioEvents || disposed || !desiredPlaying) return
    if (state.status === 'playing') state.status = 'connecting'
  }
  const onError = () => {
    if (suppressAudioEvents || disposed || !desiredPlaying) return
    void handleMediaFailure('The station stream failed')
  }
  const onStalled = () => {
    if (suppressAudioEvents || disposed || !desiredPlaying || stalledTimer) return
    stalledTimer = setTimeout(() => {
      stalledTimer = undefined
      void handleMediaFailure('The station stream stalled')
    }, 5_000)
  }

  audio.addEventListener('playing', onPlaying)
  audio.addEventListener('pause', onPause)
  audio.addEventListener('waiting', onWaiting)
  audio.addEventListener('error', onError)
  audio.addEventListener('stalled', onStalled)

  function observeCountry(countryCode: string | null): void {
    if (disposed) return
    const normalized = normalizeCountryCode(countryCode)
    if (!normalized) {
      clearDwellTimer()
      candidateCountry = null
      state.candidateCountryCode = null
      return
    }

    if (normalized === committedCountry) {
      clearDwellTimer()
      candidateCountry = null
      state.candidateCountryCode = null
      return
    }

    if (normalized === candidateCountry && dwellTimer) return
    clearDwellTimer()
    candidateCountry = normalized
    state.candidateCountryCode = normalized
    dwellTimer = setTimeout(() => {
      dwellTimer = undefined
      if (candidateCountry !== normalized || disposed) return
      candidateCountry = null
      state.candidateCountryCode = null
      commitCountry(normalized)
    }, Math.max(0, dwellMs))
  }

  async function toggle(): Promise<void> {
    if (disposed) return
    if (state.isPlaying || desiredPlaying) {
      desiredPlaying = false
      retryCycleActive = false
      clearStalledTimer()
      state.isPlaying = false
      state.status = 'paused'
      state.error = null
      detachAudio()
      return
    }

    if (!committedCountry) {
      state.status = 'waiting'
      return
    }

    desiredPlaying = true
    retryCount = 0
    state.status = 'connecting'
    state.error = null

    pruneFailedStations()
    const stationIsKnownFailed = state.station ? failedStationUuids.has(state.station.stationUuid) : false
    const station = state.station && state.station.countryCode === committedCountry && !stationIsKnownFailed
      ? state.station
      : await requestStation(committedCountry)
    if (!station || disposed || !desiredPlaying) {
      if (!disposed && desiredPlaying) finishUnavailable('No playable station is available for this country')
      return
    }

    const connected = await tryPlay(station)
    if (connected) {
      hasUserStartedPlayback = true
      retryCount = 0
      return
    }

    await runAutomaticFallback()
  }

  async function next(): Promise<void> {
    if (disposed || !committedCountry) return
    const preservePlayingIntent = state.isPlaying || desiredPlaying
    retryCycleActive = false
    retryCount = 0
    if (state.station) rememberStation(state.station.stationUuid)
    state.isPlaying = false
    state.status = preservePlayingIntent ? 'connecting' : 'paused'
    state.error = null
    desiredPlaying = preservePlayingIntent
    detachAudio()

    const station = await requestStation(committedCountry)
    if (!station || disposed) {
      if (!disposed) {
        state.status = preservePlayingIntent ? 'unavailable' : 'paused'
        state.error = 'No other playable station is available for this country'
      }
      return
    }

    if (!preservePlayingIntent) {
      state.status = 'paused'
      return
    }
    if (await tryPlay(station)) {
      hasUserStartedPlayback = true
      return
    }
    await runAutomaticFallback()
  }

  function dispose(): void {
    if (disposed) return
    disposed = true
    clearDwellTimer()
    clearStalledTimer()
    suppressAudioEvents = true
    audio.pause()
    detachAudio()
    audio.removeEventListener('playing', onPlaying)
    audio.removeEventListener('pause', onPause)
    audio.removeEventListener('waiting', onWaiting)
    audio.removeEventListener('error', onError)
    audio.removeEventListener('stalled', onStalled)
    ;(audio as AudioElementLike & { remove?: () => void }).remove?.()
  }

  function commitCountry(countryCode: string): void {
    if (disposed || countryCode === committedCountry) return
    committedCountry = countryCode
    state.countryCode = countryCode

    if (!hasUserStartedPlayback) {
      // Before the first successful user gesture the station panel should not
      // generate provider traffic or replace an already displayed station.
      state.station = null
      state.status = 'waiting'
      state.error = null
      return
    }

    // Keep the current broadcaster connected until a new eligible station is
    // returned. That preserves audio over brief provider failures and oceans.
    void selectForCommittedCountry(state.isPlaying || desiredPlaying)
  }

  async function selectForCommittedCountry(shouldPlay: boolean): Promise<void> {
    if (!committedCountry || disposed) return
    const country = committedCountry
    const station = await requestStation(country)
    if (disposed || country !== committedCountry) return
    if (!station) {
      if (!state.station) finishUnavailable('No playable station is available for this country')
      return
    }
    if (!shouldPlay) {
      state.status = 'paused'
      return
    }
    desiredPlaying = true
    state.status = 'connecting'
    if (await tryPlay(station)) {
      retryCount = 0
      return
    }
    await runAutomaticFallback()
  }

  async function requestStation(country: string): Promise<RadioStation | null> {
    const requestSequence = ++selectionSequence
    pruneFailedStations()
    try {
      const station = await api.selectStation(country, buildExclusions())
      if (disposed || requestSequence !== selectionSequence || country !== committedCountry) return null
      if (!station) return null
      state.station = station
      state.error = null
      return station
    } catch (error) {
      if (disposed || requestSequence !== selectionSequence || country !== committedCountry) return null
      state.error = error instanceof Error ? error.message : 'Station selection failed'
      return null
    }
  }

  async function tryPlay(station: RadioStation): Promise<boolean> {
    if (disposed || !desiredPlaying || station.countryCode !== committedCountry) return false
    const source = ++sourceSequence
    state.station = station
    state.status = 'connecting'
    state.isPlaying = false
    clearStalledTimer()
    setAudioSource(station.streamUrl)

    try {
      await Promise.resolve(audio.play())
    } catch (error) {
      if (!disposed && source === sourceSequence && desiredPlaying) {
        rememberFailedStation(station.stationUuid)
        void api.reportFailedStation(station.stationUuid).catch(() => undefined)
        state.error = error instanceof Error ? error.message : 'The browser could not play this stream'
        detachAudio()
      }
      return false
    }

    if (disposed || source !== sourceSequence || !desiredPlaying) return false
    state.isPlaying = true
    state.status = 'playing'
    state.error = null
    return true
  }

  async function handleMediaFailure(message: string): Promise<void> {
    if (disposed || !desiredPlaying || retryCycleActive) return
    if (state.station) {
      rememberFailedStation(state.station.stationUuid)
      void api.reportFailedStation(state.station.stationUuid).catch(() => undefined)
    }
    state.isPlaying = false
    state.status = 'retrying'
    state.error = message
    detachAudio()
    await runAutomaticFallback()
  }

  async function runAutomaticFallback(): Promise<void> {
    if (disposed || !desiredPlaying || retryCycleActive || !committedCountry) return
    retryCycleActive = true
    state.status = 'retrying'
    state.isPlaying = false
    const country = committedCountry
    detachAudio()

    while (!disposed && desiredPlaying && country === committedCountry && retryCount < Math.max(0, maxAutomaticRetries)) {
      retryCount += 1
      const station = await requestStation(country)
      if (!station || disposed || !desiredPlaying || country !== committedCountry) break
      if (await tryPlay(station)) {
        retryCycleActive = false
        retryCount = 0
        hasUserStartedPlayback = true
        return
      }
    }

    retryCycleActive = false
    if (!disposed && desiredPlaying && country === committedCountry) {
      finishUnavailable('No playable station is available after retrying')
    }
  }

  function finishUnavailable(message: string): void {
    desiredPlaying = false
    state.isPlaying = false
    state.status = 'unavailable'
    state.error = message
    detachAudio()
  }

  function setAudioSource(streamUrl: string): void {
    suppressAudioEvents = true
    try {
      audio.pause()
      audio.src = streamUrl
      audio.load?.()
    } finally {
      suppressAudioEvents = false
    }
  }

  function detachAudio(): void {
    sourceSequence += 1
    suppressAudioEvents = true
    try {
      audio.pause()
      if (typeof audio.removeAttribute === 'function') audio.removeAttribute('src')
      else audio.src = ''
      audio.load?.()
    } finally {
      suppressAudioEvents = false
    }
  }

  function clearDwellTimer(): void {
    if (dwellTimer !== undefined) clearTimeout(dwellTimer)
    dwellTimer = undefined
  }

  function clearStalledTimer(): void {
    if (stalledTimer !== undefined) clearTimeout(stalledTimer)
    stalledTimer = undefined
  }

  function buildExclusions(): string[] {
    pruneFailedStations()
    const exclusions = new Set(recentStationUuids)
    for (const stationUuid of failedStationUuids.keys()) exclusions.add(stationUuid)
    if (state.station) exclusions.add(state.station.stationUuid)
    return [...exclusions]
  }

  function rememberStation(stationUuid: string): void {
    if (!stationUuid) return
    const existingIndex = recentStationUuids.indexOf(stationUuid)
    if (existingIndex >= 0) recentStationUuids.splice(existingIndex, 1)
    recentStationUuids.push(stationUuid)
    while (recentStationUuids.length > Math.max(1, recentStationLimit)) recentStationUuids.shift()
  }

  function rememberFailedStation(stationUuid: string): void {
    if (!stationUuid) return
    failedStationUuids.delete(stationUuid)
    failedStationUuids.set(stationUuid, Date.now() + Math.max(0, failedStationTtlMs))
    while (failedStationUuids.size > Math.max(1, failedStationLimit)) {
      const oldest = failedStationUuids.keys().next().value
      if (typeof oldest !== 'string') break
      failedStationUuids.delete(oldest)
    }
  }

  function pruneFailedStations(): void {
    const now = Date.now()
    for (const [stationUuid, expiresAt] of failedStationUuids) {
      if (expiresAt <= now) failedStationUuids.delete(stationUuid)
    }
  }

  return {
    state,
    observeCountry,
    toggle,
    next,
    dispose,
    getAudioElement: () => audio,
  }
}

function normalizeCountryCode(countryCode: string | null): string | null {
  if (!countryCode) return null
  const normalized = countryCode.trim().toUpperCase()
  return /^[A-Z]{2}$/.test(normalized) ? normalized : null
}

function createBrowserAudio(): AudioElementLike {
  if (typeof document !== 'undefined') {
    const audio = document.createElement('audio')
    audio.setAttribute('aria-hidden', 'true')
    audio.style.display = 'none'
    document.body?.appendChild(audio)
    return audio
  }
  if (typeof Audio === 'function') return new Audio()
  throw new Error('Audio playback is unavailable outside a browser')
}

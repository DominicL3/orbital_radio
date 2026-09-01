import type { OrbitPosition } from '@/contracts/satellite'
import type { RadioStation } from '@/contracts/radio'

type FetchLike = (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>

export interface RadioApi {
  resolveCountry(position: Pick<OrbitPosition, 'latitudeDeg' | 'longitudeDeg'>, signal?: AbortSignal): Promise<string | null>
  selectStation(countryCode: string, excludeStationUuids?: readonly string[], signal?: AbortSignal): Promise<RadioStation | null>
  reportFailedStation(stationUuid: string, signal?: AbortSignal): Promise<void>
}

export interface RadioApiOptions {
  baseUrl?: string
  fetchImpl?: FetchLike
}

/**
 * Raised internally when an older geography request finishes after a newer
 * request. Callers should simply ignore this result; it must never replace a
 * country resolved from a more recent orbit position.
 */
export class StaleCountryRequestError extends Error {
  constructor() {
    super('The geography request was superseded by a newer orbit position')
    this.name = 'StaleCountryRequestError'
  }
}

export class RadioApiError extends Error {
  readonly status: number | undefined

  constructor(message: string, status?: number) {
    super(message)
    this.name = 'RadioApiError'
    this.status = status
  }
}

/**
 * Thin client for the application's anonymous backend API. It deliberately
 * does not know about Radio Browser mirrors or stream bytes: those concerns
 * stay on the backend and the broadcaster connection belongs to HTMLAudio.
 */
export class RadioApiClient implements RadioApi {
  private readonly baseUrl: string
  private readonly fetchImpl: FetchLike
  private countryRequestSequence = 0
  private countryAbortController: AbortController | undefined

  constructor(options: RadioApiOptions = {}) {
    this.baseUrl = normalizeBaseUrl(options.baseUrl ?? import.meta.env.VITE_API_BASE_URL ?? '')
    this.fetchImpl = options.fetchImpl ?? ((...args) => fetch(...args))
  }

  async resolveCountry(
    position: Pick<OrbitPosition, 'latitudeDeg' | 'longitudeDeg'>,
    signal?: AbortSignal,
  ): Promise<string | null> {
    const requestSequence = ++this.countryRequestSequence
    this.countryAbortController?.abort()
    const controller = new AbortController()
    this.countryAbortController = controller
    const requestSignal = combineAbortSignals(controller.signal, signal)
    const query = new URLSearchParams({
      latitude: String(position.latitudeDeg),
      longitude: String(position.longitudeDeg),
    })

    try {
      const response = await this.fetchImpl(this.url(`/geography/country?${query.toString()}`), {
        headers: { Accept: 'application/json' },
        signal: requestSignal,
      })
      if (!isSuccessful(response)) {
        throw new RadioApiError('Country lookup failed', response.status)
      }
      const payload: unknown = await response.json()
      const countryCode = parseCountryResponse(payload)
      if (requestSequence !== this.countryRequestSequence) throw new StaleCountryRequestError()
      return countryCode
    } catch (error) {
      if (requestSequence !== this.countryRequestSequence) throw new StaleCountryRequestError()
      throw error
    } finally {
      if (requestSequence === this.countryRequestSequence) this.countryAbortController = undefined
    }
  }

  async selectStation(
    countryCode: string,
    excludeStationUuids: readonly string[] = [],
    signal?: AbortSignal,
  ): Promise<RadioStation | null> {
    const normalizedCountryCode = countryCode.trim().toUpperCase()
    if (!/^[A-Z]{2}$/.test(normalizedCountryCode)) {
      throw new RadioApiError('Country code must be an ISO 3166-1 alpha-2 code')
    }

    const response = await this.fetchImpl(this.url('/radio/stations/select'), {
      method: 'POST',
      headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
      body: JSON.stringify({
        country_code: normalizedCountryCode,
        exclude_station_uuids: [...new Set(excludeStationUuids)].filter(Boolean),
      }),
      signal,
    })
    if (response.status === 204) return null
    if (!isSuccessful(response)) throw new RadioApiError('Station selection failed', response.status)
    return parseStation(await response.json())
  }

  async reportFailedStation(stationUuid: string, signal?: AbortSignal): Promise<void> {
    const normalizedUuid = stationUuid.trim()
    if (!normalizedUuid) return
    const response = await this.fetchImpl(this.url(`/radio/stations/${encodeURIComponent(normalizedUuid)}/failed`), {
      method: 'POST',
      headers: { Accept: 'application/json' },
      signal,
    })
    if (!isSuccessful(response) && response.status !== 204) {
      throw new RadioApiError('Failed-station report was rejected', response.status)
    }
  }

  private url(path: string): string {
    return `${this.baseUrl}${path.startsWith('/') ? path : `/${path}`}`
  }
}

export function createRadioApi(options: RadioApiOptions = {}): RadioApiClient {
  return new RadioApiClient(options)
}

function normalizeBaseUrl(baseUrl: string): string {
  return baseUrl.trim().replace(/\/+$/, '')
}

function isSuccessful(response: Response): boolean {
  return response.ok || (response.status >= 200 && response.status < 300)
}

function parseCountryResponse(payload: unknown): string | null {
  if (!payload || typeof payload !== 'object' || Array.isArray(payload)) {
    throw new RadioApiError('Country lookup returned an invalid response')
  }
  const countryCode = (payload as { country_code?: unknown }).country_code
  if (countryCode === null) return null
  if (typeof countryCode !== 'string' || !/^[A-Za-z]{2}$/.test(countryCode)) {
    throw new RadioApiError('Country lookup returned an invalid country code')
  }
  return countryCode.toUpperCase()
}

function parseStation(payload: unknown): RadioStation {
  if (!payload || typeof payload !== 'object' || Array.isArray(payload)) {
    throw new RadioApiError('Station selection returned an invalid response')
  }
  const station = payload as Record<string, unknown>
  const stationUuid = readString(station.station_uuid)
  const name = readString(station.name)
  const countryCode = readString(station.country_code)
  const streamUrl = readString(station.stream_url)
  const codec = readString(station.codec)
  if (!stationUuid || !name || !/^[A-Za-z]{2}$/.test(countryCode ?? '') || !streamUrl || !codec) {
    throw new RadioApiError('Station selection returned an incomplete station')
  }

  const tags = Array.isArray(station.tags)
    ? station.tags.filter((tag): tag is string => typeof tag === 'string').map((tag) => tag.trim()).filter(Boolean)
    : typeof station.tags === 'string'
      ? station.tags.split(',').map((tag) => tag.trim()).filter(Boolean)
      : []
  const bitrate = typeof station.bitrate === 'number' && Number.isFinite(station.bitrate)
    ? station.bitrate
    : station.bitrate === null || station.bitrate === undefined
      ? null
      : Number.isFinite(Number(station.bitrate))
        ? Number(station.bitrate)
        : null

  return {
    stationUuid,
    name,
    countryCode: countryCode!.toUpperCase(),
    tags,
    faviconUrl: readNullableString(station.favicon_url),
    homepageUrl: readNullableString(station.homepage_url),
    streamUrl,
    codec,
    bitrate,
  }
}

function readString(value: unknown): string | null {
  return typeof value === 'string' && value.trim() ? value.trim() : null
}

function readNullableString(value: unknown): string | null {
  return readString(value)
}

/**
 * AbortController has no standard signal-composition helper in the browsers
 * supported by this project. Keep the listener short-lived and preserve the
 * caller's signal when it is already aborted.
 */
function combineAbortSignals(internalSignal: AbortSignal, externalSignal?: AbortSignal): AbortSignal {
  if (!externalSignal) return internalSignal
  if (externalSignal.aborted) return externalSignal
  const controller = new AbortController()
  const abort = () => controller.abort()
  internalSignal.addEventListener('abort', abort, { once: true })
  externalSignal.addEventListener('abort', abort, { once: true })
  return controller.signal
}

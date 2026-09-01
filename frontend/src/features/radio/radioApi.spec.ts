import { describe, expect, it, vi } from 'vitest'
import { RadioApiClient, StaleCountryRequestError } from './radioApi'

function response(body: unknown, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  } as Response
}

const rawStation = {
  station_uuid: 'station-jp-1',
  name: 'Orbital FM',
  country_code: 'jp',
  tags: ['rock', 'jazz'],
  favicon_url: 'https://radio.example.test/favicon.png',
  homepage_url: 'https://radio.example.test',
  stream_url: 'https://radio.example.test/live.mp3',
  codec: 'MP3',
  bitrate: 128,
  hls: false,
}

describe('RadioApiClient', () => {
  it('maps normalized station fields and sends the anonymous selection contract', async () => {
    const fetchImpl = vi.fn(async () => response(rawStation))
    const api = new RadioApiClient({ baseUrl: 'http://api.example.test/', fetchImpl })

    const station = await api.selectStation('jp', ['current', 'current', 'failed'])

    expect(fetchImpl).toHaveBeenCalledWith('http://api.example.test/radio/stations/select', expect.objectContaining({
      method: 'POST',
      body: JSON.stringify({ country_code: 'JP', exclude_station_uuids: ['current', 'failed'] }),
    }))
    expect(station).toEqual({
      stationUuid: 'station-jp-1',
      name: 'Orbital FM',
      countryCode: 'JP',
      tags: ['rock', 'jazz'],
      faviconUrl: 'https://radio.example.test/favicon.png',
      homepageUrl: 'https://radio.example.test',
      streamUrl: 'https://radio.example.test/live.mp3',
      codec: 'MP3',
      bitrate: 128,
    })
  })

  it('returns null for the backend no-content response', async () => {
    const api = new RadioApiClient({ fetchImpl: vi.fn(async () => response(null, 204)) })
    await expect(api.selectStation('JP')).resolves.toBeNull()
  })

  it('resolves country codes through the backend and preserves ocean null', async () => {
    const fetchImpl = vi.fn(async () => response({ country_code: null }))
    const api = new RadioApiClient({ baseUrl: 'http://api.example.test', fetchImpl })

    await expect(api.resolveCountry({ latitudeDeg: 1.2, longitudeDeg: -3.4 })).resolves.toBeNull()
    const firstCall = fetchImpl.mock.calls[0] as unknown[] | undefined
    expect(String(firstCall?.[0])).toBe('http://api.example.test/geography/country?latitude=1.2&longitude=-3.4')
  })

  it('ignores an out-of-order country response instead of allowing stale geography to win', async () => {
    const resolvers: Array<(value: Response) => void> = []
    const fetchImpl = vi.fn(() => new Promise<Response>((resolve) => resolvers.push(resolve)))
    const api = new RadioApiClient({ fetchImpl })

    const older = api.resolveCountry({ latitudeDeg: 1, longitudeDeg: 1 })
    const newer = api.resolveCountry({ latitudeDeg: 2, longitudeDeg: 2 })
    resolvers[1]?.(response({ country_code: 'JP' }))
    await expect(newer).resolves.toBe('JP')
    resolvers[0]?.(response({ country_code: 'US' }))
    await expect(older).rejects.toBeInstanceOf(StaleCountryRequestError)
  })

  it('reports a failed UUID to the backend', async () => {
    const fetchImpl = vi.fn(async () => response(null, 204))
    const api = new RadioApiClient({ baseUrl: 'http://api.example.test', fetchImpl })

    await api.reportFailedStation('station/jp-1')
    expect(fetchImpl).toHaveBeenCalledWith('http://api.example.test/radio/stations/station%2Fjp-1/failed', expect.objectContaining({ method: 'POST' }))
  })
})

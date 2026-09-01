/**
 * The application-level station contract. Radio Browser's response shape is
 * intentionally kept behind the backend API; the Vue application only knows
 * about these normalized, camelCase fields.
 */
export interface RadioStation {
  stationUuid: string
  name: string
  countryCode: string
  tags: string[]
  faviconUrl: string | null
  homepageUrl: string | null
  streamUrl: string
  codec: string
  bitrate: number | null
}

export type RadioStatus = 'waiting' | 'connecting' | 'playing' | 'paused' | 'retrying' | 'unavailable'

export interface RadioState {
  status: RadioStatus
  isPlaying: boolean
  station: RadioStation | null
  /** The country whose station is currently selected, if any. */
  countryCode: string | null
  /** The uncommitted country currently being held for the dwell period. */
  candidateCountryCode: string | null
  error: string | null
}

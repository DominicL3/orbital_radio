export interface RadioTrack {
  id: string
  title: string
  artist: string
  artworkUrl: string
  country: string
  countryCode: string
  durationLabel: string
}

export type RadioStatus = 'ready' | 'loading' | 'empty'

export interface RadioState {
  status: RadioStatus
  isPlaying: boolean
  track: RadioTrack | null
}

export interface SatelliteCatalogEntry {
  id: string
  name: string
  noradId: number
  category: 'iss' | 'weather' | 'earth-observation' | 'communication'
  description: string
  accentColor: string
}

export interface OrbitPosition {
  timestamp: Date
  longitudeDeg: number
  latitudeDeg: number
  altitudeKm: number
}

export interface OrbitPositionSource {
  readonly satelliteId: string
  getPosition(at: Date): OrbitPosition
  getPath?(at: Date, samples: number): OrbitPosition[]
}

export interface SimulationState {
  isPlaying: boolean
  speed: 1 | 10 | 60
}

export interface SelectedSatelliteState {
  selectedSatelliteId: string | null
}

import type { SatelliteCatalogEntry } from '@/contracts/satellite'

export const issCatalogEntry: SatelliteCatalogEntry = {
  id: 'iss',
  name: 'International Space Station',
  noradId: 25544,
  category: 'iss',
  description: 'Low Earth orbit laboratory · simulated visual trajectory',
  accentColor: '#82caff',
}

export const satelliteCatalog = [issCatalogEntry]

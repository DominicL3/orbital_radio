import * as Cesium from 'cesium'

const SENTINEL_2_ASSET_ID = 3954
const COUNTRY_BOUNDARIES_URL = '/data/ne_10m_admin_0_boundary_lines_land.geojson'
const COUNTRY_LABELS_URL = '/data/ne_10m_admin_0_label_points.geojson'
const COUNTRY_SCALE_MINIMUM_ZOOM_DISTANCE = 100_000

type CountryLabelProperties = {
  scalerank?: number
  sr_adm0_a3?: string
  sr_subunit?: string
}

function configureIonAccessToken(token?: string): boolean {
  if (!token?.trim() || !Cesium.Ion) return false
  Cesium.Ion.defaultAccessToken = token
  return true
}

export function createSentinel2BaseLayer(token?: string): Cesium.ImageryLayer | false {
  if (!configureIonAccessToken(token) || !Cesium.ImageryLayer?.fromProviderAsync || !Cesium.IonImageryProvider?.fromAssetId) {
    return false
  }

  return Cesium.ImageryLayer.fromProviderAsync(
    Cesium.IonImageryProvider.fromAssetId(SENTINEL_2_ASSET_ID),
  )
}

export function createWorldTerrain(token?: string): Cesium.Terrain | false {
  if (!configureIonAccessToken(token) || !Cesium.Terrain?.fromWorldTerrain) return false

  return Cesium.Terrain.fromWorldTerrain({
    requestVertexNormals: true,
  })
}

export function applyCountryScaleZoomLimit(viewer: {
  scene?: { screenSpaceCameraController?: { minimumZoomDistance: number } }
}): void {
  const controller = viewer.scene?.screenSpaceCameraController
  if (controller) controller.minimumZoomDistance = COUNTRY_SCALE_MINIMUM_ZOOM_DISTANCE
}

export async function addCountryReference(viewer: Cesium.Viewer): Promise<Cesium.DataSource[]> {
  if (!viewer.dataSources || !Cesium.GeoJsonDataSource?.load || !Cesium.Color || !Cesium.DistanceDisplayCondition) return []

  const borderColor = Cesium.Color.fromCssColorString('#d9f2f4').withAlpha(0.72)
  const labelColor = Cesium.Color.fromCssColorString('#f1fcff')

  const [borders, labels] = await Promise.all([
    Cesium.GeoJsonDataSource.load(COUNTRY_BOUNDARIES_URL, {
      stroke: borderColor,
      strokeWidth: 1.15,
      fill: Cesium.Color.TRANSPARENT,
      clampToGround: true,
    }),
    Cesium.GeoJsonDataSource.load(COUNTRY_LABELS_URL, {
      clampToGround: true,
    }),
  ])

  const bestLabelByCountry = new Map<string, { entity: Cesium.Entity; scaleRank: number }>()

  for (const entity of labels.entities.values) {
    const properties = entity.properties?.getValue(Cesium.JulianDate.now()) as CountryLabelProperties | undefined
    const countryId = properties?.sr_adm0_a3
    const name = properties?.sr_subunit
    if (!countryId || !name) {
      entity.show = false
      continue
    }

    const scaleRank = properties.scalerank ?? Number.POSITIVE_INFINITY
    const previousLabel = bestLabelByCountry.get(countryId)
    if (previousLabel && previousLabel.scaleRank <= scaleRank) {
      entity.show = false
      continue
    }

    if (previousLabel) previousLabel.entity.show = false
    bestLabelByCountry.set(countryId, { entity, scaleRank })

    entity.billboard = undefined
    entity.label = {
      text: String(name),
      font: '600 14px ui-sans-serif, system-ui, sans-serif',
      fillColor: labelColor,
      outlineColor: Cesium.Color.BLACK.withAlpha(0.65),
      outlineWidth: 3,
      style: Cesium.LabelStyle.FILL_AND_OUTLINE,
      heightReference: Cesium.HeightReference.CLAMP_TO_GROUND,
      distanceDisplayCondition: new Cesium.DistanceDisplayCondition(500_000, 12_000_000),
      disableDepthTestDistance: Number.POSITIVE_INFINITY,
    } as never
  }

  viewer.dataSources.add(borders)
  viewer.dataSources.add(labels)
  return [borders, labels]
}

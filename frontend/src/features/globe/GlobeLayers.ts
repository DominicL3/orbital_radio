import * as Cesium from 'cesium'

const GOOGLE_SATELLITE_WITH_LABELS_ASSET_ID = 3830183
const COUNTRY_SCALE_MINIMUM_ZOOM_DISTANCE = 100_000

function configureIonAccessToken(token?: string): boolean {
  if (!token?.trim() || !Cesium.Ion) return false
  Cesium.Ion.defaultAccessToken = token
  return true
}

export function createGoogleSatelliteWithLabelsBaseLayer(token?: string): Cesium.ImageryLayer | false {
  if (!configureIonAccessToken(token) || !Cesium.ImageryLayer?.fromProviderAsync || !Cesium.IonImageryProvider?.fromAssetId) {
    return false
  }

  return Cesium.ImageryLayer.fromProviderAsync(
    Cesium.IonImageryProvider.fromAssetId(GOOGLE_SATELLITE_WITH_LABELS_ASSET_ID),
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

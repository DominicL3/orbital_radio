import { describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import CesiumGlobe from './CesiumGlobe.vue'
import { issCatalogEntry } from '@/fixtures/iss'

vi.mock('cesium', () => ({ Viewer: vi.fn() }))

describe('CesiumGlobe', () => {
  it('labels the rendered ISS experience as a simulation', () => {
    const wrapper = mount(CesiumGlobe, { props: { satellite: issCatalogEntry, isPlaying: true, speed: 1, showOrbitPath: true } })
    expect(wrapper.attributes('aria-label')).toContain('simulation')
  })

  it('emits an initial simulated orbit position for country resolution', () => {
    const wrapper = mount(CesiumGlobe, { props: { satellite: issCatalogEntry, isPlaying: true, speed: 1, showOrbitPath: true } })
    const positions = wrapper.emitted('position-updated')
    expect(positions).toHaveLength(1)
    expect(positions?.[0]?.[0]).toMatchObject({ latitudeDeg: expect.any(Number), longitudeDeg: expect.any(Number) })
  })
})

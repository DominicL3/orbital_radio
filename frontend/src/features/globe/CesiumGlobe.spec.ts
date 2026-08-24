import { describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import CesiumGlobe from './CesiumGlobe.vue'
import { issCatalogEntry } from '@/fixtures/iss'

vi.mock('cesium', () => ({ Viewer: vi.fn() }))

describe('CesiumGlobe', () => {
  it('labels the rendered ISS experience as a simulation', () => {
    const wrapper = mount(CesiumGlobe, { props: { satellite: issCatalogEntry, isPlaying: true, speed: 1, showOrbitPath: true } })
    expect(wrapper.text()).toContain('SIMULATION')
  })
})

import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import ExplorerControls from './ExplorerControls.vue'

describe('ExplorerControls', () => {
  it('emits simulation and orbit actions', async () => {
    const wrapper = mount(ExplorerControls, { props: { isPlaying: true, speed: 1, showOrbitPath: true } })
    await wrapper.get('[aria-label="Pause simulation"]').trigger('click')
    await wrapper.get('[aria-label="Set simulation speed to 10x"]').trigger('click')
    await wrapper.get('[aria-label="Hide orbit path"]').trigger('click')
    expect(wrapper.emitted('toggle-play')).toHaveLength(1)
    expect(wrapper.emitted('set-speed')?.[0]).toEqual([10])
    expect(wrapper.emitted('toggle-orbit-path')).toHaveLength(1)
  })
})

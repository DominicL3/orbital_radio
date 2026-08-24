import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import RadioPanel from './RadioPanel.vue'
import { mockRadioTracks } from '@/fixtures/radio'

describe('RadioPanel', () => {
  it('renders fixture track context and emits controls', async () => {
    const wrapper = mount(RadioPanel, { props: { state: { status: 'ready', isPlaying: false, track: mockRadioTracks[0] } } })
    expect(wrapper.text()).toContain('Night Drive')
    expect(wrapper.text()).toContain('Japan')
    await wrapper.get('[aria-label="Play radio"]').trigger('click')
    await wrapper.get('[aria-label="Skip track"]').trigger('click')
    expect(wrapper.emitted('toggle-play')).toHaveLength(1)
    expect(wrapper.emitted('next-track')).toHaveLength(1)
  })
})

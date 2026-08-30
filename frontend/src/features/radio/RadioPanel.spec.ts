import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import RadioPanel from './RadioPanel.vue'
import { mockRadioTracks } from '@/fixtures/radio'

describe('RadioPanel', () => {
  it('renders fixture track context and emits controls', async () => {
    const wrapper = mount(RadioPanel, { props: { state: { status: 'ready', isPlaying: false, track: mockRadioTracks[0] } } })
    expect(wrapper.text()).toContain('Night Drive')
    expect(wrapper.text()).toContain('Japan')
    expect(wrapper.findAll('.signal-line i')).toHaveLength(36)
    expect(wrapper.findAll('.signal-line i.is-playing')).toHaveLength(0)
    await wrapper.get('[aria-label="Play radio"]').trigger('click')
    await wrapper.get('[aria-label="Skip track"]').trigger('click')
    expect(wrapper.emitted('toggle-play')).toHaveLength(1)
    expect(wrapper.emitted('next-track')).toHaveLength(1)
  })

  it('animates the spectrum only while the radio is playing', async () => {
    const wrapper = mount(RadioPanel, { props: { state: { status: 'ready', isPlaying: false, track: mockRadioTracks[0] } } })

    await wrapper.setProps({ state: { status: 'ready', isPlaying: true, track: mockRadioTracks[0] } })

    expect(wrapper.findAll('.signal-line i.is-playing')).toHaveLength(36)
  })
})

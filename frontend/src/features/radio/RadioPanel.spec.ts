import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import type { RadioState, RadioStation } from '@/contracts/radio'
import RadioPanel from './RadioPanel.vue'

const station: RadioStation = {
  stationUuid: 'jp-1',
  name: 'Orbital FM',
  countryCode: 'JP',
  tags: ['rock', 'jazz'],
  faviconUrl: 'https://radio.example.test/favicon.png',
  homepageUrl: 'https://radio.example.test',
  streamUrl: 'https://radio.example.test/live.mp3',
  codec: 'MP3',
  bitrate: 128,
}

function state(overrides: Partial<RadioState> = {}): RadioState {
  return {
    status: 'paused',
    isPlaying: false,
    volume: 70,
    station,
    countryCode: 'JP',
    candidateCountryCode: null,
    error: null,
    ...overrides,
  }
}

describe('RadioPanel', () => {
  it('renders station context, live status, tags, and controls', async () => {
    const wrapper = mount(RadioPanel, { props: { state: state() } })

    expect(wrapper.text()).toContain('Orbital FM')
    expect(wrapper.text()).toContain('JP')
    expect(wrapper.text()).toContain('rock')
    expect(wrapper.text()).toContain('jazz')
    expect(wrapper.text()).not.toContain('duration')
    expect(wrapper.find('.progress-track').exists()).toBe(false)
    expect(wrapper.findAll('.signal-line i')).toHaveLength(36)
    expect(wrapper.findAll('.signal-line i.is-playing')).toHaveLength(0)
    expect(wrapper.get('[aria-label="Radio volume"]').attributes('min')).toBe('0')
    expect(wrapper.get('[aria-label="Radio volume"]').attributes('max')).toBe('100')
    expect(wrapper.get('output').text()).toBe('70%')

    await wrapper.get('[aria-label="Play radio"]').trigger('click')
    await wrapper.get('[aria-label="Next station"]').trigger('click')
    expect(wrapper.emitted('toggle-play')).toHaveLength(1)
    expect(wrapper.emitted('next-station')).toHaveLength(1)
  })

  it('emits an accessible volume-slider change', async () => {
    const wrapper = mount(RadioPanel, { props: { state: state({ volume: 36 }) } })
    const slider = wrapper.get('[aria-label="Radio volume"]')

    expect(slider.attributes('aria-valuetext')).toBe('36%')
    expect(wrapper.get('output').text()).toBe('36%')
    await slider.setValue('18')

    expect(wrapper.emitted('set-volume')).toEqual([[18]])
  })

  it('animates the signal only while the station is playing', async () => {
    const wrapper = mount(RadioPanel, { props: { state: state() } })
    await wrapper.setProps({ state: state({ status: 'playing', isPlaying: true }) })
    expect(wrapper.findAll('.signal-line i.is-playing')).toHaveLength(36)
    expect(wrapper.get('[aria-label="Pause radio"]').attributes('disabled')).toBeUndefined()
  })

  it('keeps Play disabled until a land country is committed', () => {
    const wrapper = mount(RadioPanel, { props: { state: state({ station: null, countryCode: null, status: 'waiting' }) } })
    expect(wrapper.get('[aria-label="Play radio"]').attributes('disabled')).toBeDefined()
    expect(wrapper.text()).toContain('Waiting for a land signal')
  })

  it('allows the initial gesture once a country is committed even before station selection', () => {
    const wrapper = mount(RadioPanel, { props: { state: state({ station: null, countryCode: 'JP', status: 'waiting' }) } })
    expect(wrapper.get('[aria-label="Play radio"]').attributes('disabled')).toBeUndefined()
  })

  it('falls back to the station glyph when its favicon fails', async () => {
    const wrapper = mount(RadioPanel, { props: { state: state() } })
    await wrapper.get('img').trigger('error')
    expect(wrapper.find('img').exists()).toBe(false)
    expect(wrapper.find('.artwork-glyph').exists()).toBe(true)
  })
})

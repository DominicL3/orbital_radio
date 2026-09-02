import { expect, test, type Page } from '@playwright/test'

const station = (stationUuid: string, name: string) => ({
  station_uuid: stationUuid,
  name,
  country_code: 'JP',
  tags: ['rock', 'electronic'],
  favicon_url: 'https://radio.example.test/favicon.png',
  homepage_url: 'https://radio.example.test',
  stream_url: `https://radio.example.test/${stationUuid}.mp3`,
  codec: 'MP3',
  bitrate: 128,
})

async function mockRadioBackend(page: Page) {
  let stationIndex = 0
  await page.route('**/geography/country*', async (route) => {
    await route.fulfill({ json: { country_code: 'JP' } })
  })
  await page.route('**/radio/stations/select', async (route) => {
    const body = route.request().postDataJSON() as { exclude_station_uuids?: string[] }
    const excluded = new Set(body.exclude_station_uuids ?? [])
    const candidates = [station('jp-1', 'Orbital FM One'), station('jp-2', 'Orbital FM Two'), station('jp-3', 'Orbital FM Three')]
    const selected = candidates.find((candidate) => !excluded.has(candidate.station_uuid)) ?? candidates[stationIndex % candidates.length]
    stationIndex += 1
    await route.fulfill({ json: selected })
  })
  await page.route('**/radio/stations/*/failed', async (route) => {
    await route.fulfill({ status: 204 })
  })
}

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    HTMLMediaElement.prototype.play = () => Promise.resolve()
    HTMLMediaElement.prototype.pause = () => undefined
    HTMLMediaElement.prototype.load = () => undefined
  })
  await mockRadioBackend(page)
})

test('shows the radio and mission-control overlays with a mocked land lookup', async ({ page }) => {
  await page.goto('/')

  await expect(page.getByText('01 TARGET ONLINE')).toBeVisible()
  await expect(page.getByRole('button', { name: 'Pause simulation' })).toBeVisible()
  const playButton = page.getByRole('button', { name: 'Play radio' })
  await expect(playButton).toBeEnabled({ timeout: 6_000 })
  await expect(page.getByText('Waiting for a land signal')).toHaveCount(0)
})

test('starts, pauses, reconnects, and skips mocked live stations without public radio traffic', async ({ page }) => {
  await page.goto('/')
  const playButton = page.getByRole('button', { name: 'Play radio' })
  await expect(playButton).toBeEnabled({ timeout: 6_000 })

  const volumeSlider = page.getByLabel('Radio volume')
  await volumeSlider.evaluate((input: HTMLInputElement) => {
    input.value = '36'
    input.dispatchEvent(new Event('input', { bubbles: true }))
  })
  await expect(volumeSlider).toHaveValue('36')
  await expect.poll(() => page.locator('audio').evaluate((audio: HTMLAudioElement) => audio.volume)).toBe(0.36)

  await playButton.click()
  await expect(page.getByText('Orbital FM One')).toBeVisible()
  await expect(page.getByText('ON AIR')).toBeVisible()

  await page.getByRole('button', { name: 'Next station' }).click()
  await expect(page.getByText('Orbital FM Two')).toBeVisible()
  await expect(page.getByText('ON AIR')).toBeVisible()

  await page.getByRole('button', { name: 'Pause radio' }).click()
  await expect(page.locator('.live-mark')).toContainText('PAUSED')
  await page.getByRole('button', { name: 'Play radio' }).click()
  await expect(page.getByText('ON AIR')).toBeVisible()
})

test('uses one audio element and falls back after a mocked media error', async ({ page }) => {
  await page.goto('/')
  const playButton = page.getByRole('button', { name: 'Play radio' })
  await expect(playButton).toBeEnabled({ timeout: 6_000 })
  await playButton.click()
  await expect(page.getByText('Orbital FM One')).toBeVisible()

  await page.evaluate(() => {
    const audio = document.querySelector('audio')
    if (!audio) throw new Error('Expected the radio controller to own one audio element')
    audio.dispatchEvent(new Event('error'))
  })
  await expect(page.getByText('Orbital FM Two')).toBeVisible()
  await expect(page.locator('audio')).toHaveCount(1)
})

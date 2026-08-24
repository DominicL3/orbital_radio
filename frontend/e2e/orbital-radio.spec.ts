import { expect, test } from '@playwright/test'

test('shows the radio and mission-control overlays', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByText('Night Drive')).toBeVisible()
  await expect(page.getByText('01 TARGET ONLINE')).toBeVisible()
  await expect(page.getByRole('button', { name: 'Pause simulation' })).toBeVisible()
})

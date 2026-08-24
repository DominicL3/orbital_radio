import { expect, test } from '@playwright/test'

test('shows the ISS groove and radio overlay', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByRole('heading', { name: 'ISS GROOVE' })).toBeVisible()
  await expect(page.getByText('Night Drive')).toBeVisible()
  await expect(page.getByRole('button', { name: 'Pause simulation' })).toBeVisible()
})

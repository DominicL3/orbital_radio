import { expect, test } from '@playwright/test'

test('shows the ISS groove and radio overlay', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByRole('heading', { name: 'ISS GROOVE' })).toBeVisible()
  await expect(page.getByText('Night Drive')).toBeVisible()
  await expect(page.getByRole('button', { name: 'Pause simulation' })).toBeVisible()
})

test.describe('desktop title block layout', () => {
  for (const width of [1280, 1920]) {
    test(`${width}px keeps the title block stable and clear of the tracking target`, async ({ page }) => {
      await page.setViewportSize({ width, height: 720 })
      await page.goto('/')

      const titleBlock = page.locator('.title-block')
      const title = titleBlock.getByRole('heading', { name: 'ISS GROOVE' })
      const description = titleBlock.locator('.title-description')
      const target = page.locator('.target-overlay')

      await expect(titleBlock).toBeVisible()
      await expect(title).toBeVisible()
      await expect(description).toBeVisible()

      const titleBlockBox = await titleBlock.boundingBox()
      const titleBox = await title.boundingBox()
      const descriptionBox = await description.boundingBox()
      const targetBox = await target.boundingBox()
      const titleFontSize = await title.evaluate((element) => getComputedStyle(element).fontSize)

      expect(titleBlockBox?.y).toBe(120)
      expect(titleBox?.y).toBeGreaterThanOrEqual(titleBlockBox?.y ?? 0)
      expect(descriptionBox?.y).toBeGreaterThan(titleBox?.y ?? 0)
      expect(titleFontSize).toBe('74px')
      expect(titleBlockBox && targetBox).toBeTruthy()
      expect(titleBlockBox!.y + titleBlockBox!.height).toBeLessThanOrEqual(targetBox!.y)
      await expect(page.locator('.cesium-globe__simulation')).toHaveCount(0)
    })
  }
})

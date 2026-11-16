import { expect, test } from '@playwright/test'

test('a full daily session runs to completion', async ({ page }, testInfo) => {
  // Both projects share one database; run the session once so the schedule is predictable.
  test.skip(testInfo.project.name !== 'desktop', 'daily session runs on desktop only')
  await page.goto('/#/today')
  await expect(page.getByRole('heading', { name: 'Today', exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'Start session' }).click()
  const bar = page.getByRole('progressbar', { name: 'Session progress' })
  const total = Number(await bar.getAttribute('aria-valuemax'))
  for (let i = 0; i < total; i += 1) {
    // Wait for the next question to finish loading (inputs are disabled while it does).
    await expect(page.locator('input:enabled, .choices button:enabled').first()).toBeVisible()
    const input = page.getByLabel('Your answer')
    if (await input.isVisible()) {
      await input.fill('1')
      await input.press('Enter')
    } else {
      await page.keyboard.press('1')
    }
    await expect(page.getByRole('heading', { name: /Correct|Not quite/ })).toBeVisible()
    await page.getByRole('button', { name: /Next/ }).click()
  }
  await expect(page.getByRole('heading', { name: 'Session complete' })).toBeVisible()
})

test('the curriculum links concepts, drills and lectures', async ({ page }) => {
  await page.goto('/#/learn')
  await expect(page.getByRole('heading', { name: 'Curriculum' })).toBeVisible()
  await page.getByRole('link', { name: /Counting outs/ }).click()
  await expect(page.getByRole('heading', { name: 'Counting outs' })).toBeVisible()
  await expect(page.getByRole('link', { name: /2016 L1/ })).toHaveAttribute('href', /ocw\.mit\.edu/)
  await page.getByRole('link', { name: 'Count your outs' }).click()
  await expect(page.getByLabel('Your answer')).toBeVisible()
})

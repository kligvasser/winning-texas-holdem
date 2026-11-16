import { answerAnything } from './answer'
import { expect, test } from '@playwright/test'

test('a full daily session runs to completion', async ({ page }, testInfo) => {
  // Both projects share one database; run the session once so the schedule is predictable.
  test.skip(testInfo.project.name !== 'desktop', 'daily session runs on desktop only')
  await page.goto('/#/today')
  await expect(page.getByRole('heading', { name: 'Today', exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'Start session' }).click()
  // Multi-street items (hand stories, hand reading) take several answers, so answer until done.
  const done = page.getByRole('heading', { name: 'Session complete' })
  for (let i = 0; i < 80 && !(await done.isVisible()); i += 1) {
    await answerAnything(page)
    await page.getByRole('button', { name: /Next/ }).click()
    await expect(done.or(page.locator('.prompt'))).toBeVisible()
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

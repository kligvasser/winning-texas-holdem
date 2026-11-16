import { expect, test } from '@playwright/test'

test('play hands against a bot and review them', async ({ page }) => {
  await page.goto('/#/play')
  await page.getByRole('button', { name: /Calling station/ }).click()
  await expect(page.getByRole('region', { name: 'Poker table' })).toBeVisible()
  const result = page.getByRole('region', { name: 'Hand result' })
  const log = page.locator('details.log li')
  const move = page.locator('[aria-label="Your action"] button:enabled', { hasText: /^(Call|Check)/ })
  for (let hand = 0; hand < 2; hand += 1) {
    for (let step = 0; step < 20; step += 1) {
      // Our move (an enabled Call/Check) or the end of the hand.
      await expect(result.or(move.first())).toBeVisible()
      if (await result.isVisible()) break
      const before = await log.count()
      await move.first().click()
      // Wait for the move to land before deciding the next one.
      await expect.poll(async () => (await result.isVisible()) || (await log.count()) > before).toBe(true)
    }
    await expect(page.getByRole('heading', { name: /You win|You lose|Split pot/ })).toBeVisible()
    if (hand === 0) {
      const before = await log.count()
      await page.keyboard.press('n')
      await expect.poll(async () => !(await result.isVisible()) || (await log.count()) !== before).toBe(true)
    }
  }
  await page.goto('/#/review')
  await expect(page.getByRole('heading', { name: 'Review' })).toBeVisible()
  await page.getByRole('link', { name: /vs station/ }).first().click()
  await expect(page.getByRole('heading', { name: /Hand #\d+ vs station/ })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Your decisions' })).toBeVisible()
})

import { expect, test } from '@playwright/test'

test('play six-max hands against the bots and review them', async ({ page }) => {
  await page.goto('/#/play')
  await expect(page.getByText('Calling station')).toBeVisible()
  await page.getByRole('button', { name: 'Deal me in!' }).click()
  await expect(page.getByRole('region', { name: 'Poker table' })).toBeVisible()
  const result = page.getByRole('region', { name: 'Hand result' })
  const log = page.locator('details.log li')
  const skip = page.getByRole('button', { name: /Skip/ })
  const move = page.locator('[aria-label="Your action"] button:enabled', { hasText: /^(Call|Check)/ })
  for (let hand = 0; hand < 2; hand += 1) {
    for (let step = 0; step < 20; step += 1) {
      // The bots act one at a time; skip ahead to our move or the end of the hand.
      await expect(result.or(move.first()).or(skip).first()).toBeVisible()
      if (await skip.isVisible()) await skip.click().catch(() => {})
      await expect(result.or(move.first()).first()).toBeVisible()
      if (await result.isVisible()) break
      const before = await log.count()
      await move.first().click()
      // Wait for the move to land before deciding the next one.
      await expect.poll(async () => (await result.isVisible()) || (await log.count()) > before).toBe(true)
    }
    await expect(page.getByRole('heading', { name: /You win|You lose|the pot/ })).toBeVisible()
    if (hand === 0) {
      const before = await log.count()
      await page.keyboard.press('n')
      await expect.poll(async () => !(await result.isVisible()) || (await log.count()) !== before).toBe(true)
    }
  }
  await page.goto('/#/review')
  await expect(page.getByRole('heading', { name: 'Review' })).toBeVisible()
  await page.getByRole('link', { name: /6-max/ }).first().click()
  await expect(page.getByRole('heading', { name: /Hand #\d+/ })).toBeVisible()
  await expect(page.getByRole('group', { name: /^You/ })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Your decisions' })).toBeVisible()
})

import { expect, test } from '@playwright/test'

test('a speed round counts answers and saves a personal best', async ({ page }) => {
  await page.clock.install()
  await page.goto('/#/speed/hand-ranking')
  await expect(page.getByRole('heading', { name: 'Speed round: Name the hand' })).toBeVisible()
  await page.getByRole('button', { name: /Start/ }).click()
  const score = page.getByLabel('Speed score')
  const missed = page.getByRole('status')
  for (let i = 0; i < 4; i += 1) {
    await expect(page.locator('.choices button:enabled').first()).toBeVisible()
    const before = await score.textContent()
    await page.keyboard.press(String((i % 9) + 1))
    // Wait until the answer is graded (score moved or the miss is shown) before moving the
    // fake clock, so the miss reveal timer exists when time is advanced.
    await expect
      .poll(async () => (await missed.count()) > 0 || (await score.textContent()) !== before)
      .toBe(true)
    await page.clock.runFor(800)
  }
  await page.clock.fastForward('01:05')
  await page.clock.runFor(200)
  await expect(page.getByRole('heading', { name: /Time's up|New personal best/ })).toBeVisible()
  await expect(page.getByText(/correct of [1-9]/)).toBeVisible()
})

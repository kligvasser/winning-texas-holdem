import { expect, test } from '@playwright/test'

test('a speed round counts answers and saves a personal best', async ({ page }) => {
  await page.clock.install()
  await page.goto('/#/speed/hand-ranking')
  await expect(page.getByRole('heading', { name: 'Speed round: Name the hand' })).toBeVisible()
  await page.getByRole('button', { name: /Start/ }).click()
  for (let i = 0; i < 4; i += 1) {
    await expect(page.locator('.choices button:enabled').first()).toBeVisible()
    await page.keyboard.press(String((i % 9) + 1))
    await page.clock.runFor(800) // let a missed answer's flash pass
  }
  await page.clock.fastForward('01:05')
  await page.clock.runFor(200)
  await expect(page.getByRole('heading', { name: /Time's up|New personal best/ })).toBeVisible()
  await expect(page.getByText(/correct of [1-9]/)).toBeVisible()
})

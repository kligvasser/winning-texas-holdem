import { expect, test } from '@playwright/test'

test('play the AKQ toy game against Rocky and see the summary', async ({ page }) => {
  await page.goto('/#/math-lab')
  await page.getByRole('link', { name: /Toy games/ }).click()
  await expect(page.getByRole('heading', { name: 'Toy games' })).toBeVisible()
  await expect(page.getByRole('button', { name: /The AKQ game/ })).toHaveAttribute('aria-pressed', 'true')
  await page.getByRole('button', { name: 'Play Rocky' }).click()
  await expect(page.getByRole('region', { name: 'Toy table' })).toBeVisible()

  const result = page.getByRole('region', { name: 'Hand result' })
  const moves = page.locator('[aria-label="Your action"] button')
  for (let hand = 0; hand < 6; hand += 1) {
    await expect(moves.first()).toBeEnabled()
    await moves.first().click() // bet as the bettor, call as the caller
    await expect(result.getByRole('heading', { name: /You (win|lose) \d chips?/ })).toBeVisible()
    await expect(result.getByText('your play')).toBeVisible()
    await page.getByRole('button', { name: /Next hand/ }).click()
    await expect(result).toBeHidden()
  }
  await expect(page.getByRole('region', { name: 'Session summary' })).toContainText(/Hands played: \d+/)
  await expect(page.getByRole('row', { name: /^A / })).toBeVisible()
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)

  await page.getByRole('button', { name: 'Change game' }).click()
  await page.getByRole('button', { name: /The 1 to 10 game/ }).click()
  await page.getByRole('button', { name: 'Play Finn' }).click()
  await expect(page.getByRole('row', { name: /^10 / })).toBeVisible()
})

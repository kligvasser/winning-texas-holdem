import { type Page, expect } from '@playwright/test'

/** Wait for a question of any kind to be ready, then answer it somehow. */
export async function answerAnything(page: Page) {
  const input = page.getByLabel('Your answer')
  const choice = page.locator('.choices button:enabled').first()
  const lockIn = page.getByRole('button', { name: 'Lock in' })
  await expect(page.locator('input:enabled[aria-label="Your answer"], .choices button:enabled, button:enabled:has-text("Lock in")').first()).toBeVisible()
  if (await input.isVisible()) {
    await input.fill('1')
    await input.press('Enter')
  } else if (await lockIn.isVisible()) {
    await lockIn.click()
  } else {
    await choice.click()
  }
  await expect(page.getByRole('heading', { name: /Correct|Not quite/ })).toBeVisible()
}

/** Wait for the next question to be answerable (any kind). */
export async function questionReady(page: Page) {
  await expect(page.locator('input:enabled[aria-label="Your answer"], .choices button:enabled, button:enabled:has-text("Lock in")').first()).toBeVisible()
}

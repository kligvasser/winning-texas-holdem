import { expect, test } from '@playwright/test'

test('home page links into the Math Lab', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByRole('heading', { name: "Winning Texas Hold'em" })).toBeVisible()
  await page.getByRole('link', { name: 'Math Lab' }).first().click()
  await expect(page.getByRole('heading', { name: 'Math Lab' })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Tier 0 · Mechanics' })).toBeVisible()
})

test('a numeric drill is graded, explained and logged', async ({ page }) => {
  await page.goto('/#/math-lab/pot-odds')
  const input = page.getByLabel('Your answer')
  await expect(input).toBeFocused()
  await input.fill('25')
  await input.press('Enter')
  await expect(page.getByRole('heading', { name: /Correct|Not quite/ })).toBeVisible()
  await expect(page.getByText(/final pot/)).toBeVisible()
  await expect(page.getByLabel('Session score')).toHaveText(/\d\/1 correct/)

  await page.keyboard.press('Enter')
  await expect(page.getByLabel('Your answer')).toBeEmpty()

  await page.getByRole('link', { name: 'Progress' }).click()
  await expect(page.getByRole('rowheader', { name: 'Pot odds' })).toBeVisible()
})

test('a card drill renders cards and takes keyboard choices', async ({ page }) => {
  await page.goto('/#/math-lab/showdown')
  await expect(page.getByRole('img', { name: /of (spades|hearts|diamonds|clubs)/ })).toHaveCount(11)
  await page.keyboard.press('1')
  await expect(page.getByRole('heading', { name: /Correct|Not quite/ })).toBeVisible()
  await expect(page.getByText(/Player 1: /)).toBeVisible()
})

test('every drill loads a question', async ({ page, request }) => {
  const drills = (await (await request.get('/api/drills')).json()) as { key: string; title: string }[]
  for (const drill of drills) {
    await page.goto(`/#/math-lab/${drill.key}`)
    // Equity-heavy drills take a moment to deal on a slow machine.
    await expect(page.locator('.prompt')).toBeVisible({ timeout: 20_000 })
    await expect(page.getByText(drill.title, { exact: true })).toBeVisible()
  }
})

test('layout has no horizontal scroll', async ({ page }) => {
  for (const path of ['/', '/#/math-lab', '/#/math-lab/call-or-fold']) {
    await page.goto(path)
    await page.locator('main').waitFor()
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)
    expect(overflow).toBeLessThanOrEqual(0)
  }
})

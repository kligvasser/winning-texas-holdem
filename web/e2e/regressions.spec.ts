import { expect, test } from '@playwright/test'

test('friendly number formats are accepted', async ({ page }) => {
  await page.goto('/#/math-lab/pot-odds')
  for (const text of ['25%', '0,25', '1/4']) {
    const input = page.getByLabel('Your answer')
    await expect(input).toBeEnabled()
    await input.fill(text)
    await input.press('Enter')
    await expect(page.getByRole('heading', { name: /Correct|Not quite/ })).toBeVisible()
    await page.getByRole('button', { name: /Next/ }).click()
  }
  await expect(page.getByLabel('Your answer')).toBeEnabled()
  await page.getByLabel('Your answer').fill('lots')
  await page.getByLabel('Your answer').press('Enter')
  await expect(page.getByText('Type a number, like 25, 25% or 1/3.')).toBeVisible()
})

test('browser shortcuts with digits do not answer', async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== 'desktop', 'keyboard shortcuts are a desktop concern')
  await page.goto('/#/math-lab/showdown')
  await expect(page.locator('.prompt')).toBeVisible()
  await page.keyboard.press('Control+1')
  await page.keyboard.press('Meta+2')
  await expect(page.getByRole('heading', { name: /Correct|Not quite/ })).toHaveCount(0)
  await page.keyboard.press('1')
  await expect(page.getByRole('heading', { name: /Correct|Not quite/ })).toBeVisible()
  await expect(page.locator('.choices button.right')).toHaveCount(1)
})

test('a daily session resumes after a reload', async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== 'phone', 'desktop runs the full-session test')
  await page.goto('/#/today')
  await page.getByRole('button', { name: /Start session|Resume session/ }).first().click()
  await expect(page.locator('input:enabled, .choices button:enabled').first()).toBeVisible()
  await page.getByRole('button', { name: 'Skip' }).click()
  await expect(page.getByText(/^Question 2 of/)).toBeVisible()
  await page.reload()
  await expect(page.getByText(/You have a session in progress: question 2 of/)).toBeVisible()
  await page.getByRole('button', { name: 'Resume session' }).click()
  await expect(page.getByText(/^Question 2 of/)).toBeVisible()
})

test('painting on a phone: taps toggle and swipes scroll', async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== 'phone', 'touch behaviour')
  await page.setViewportSize({ width: 412, height: 560 }) // short enough that the page scrolls
  await page.goto('/#/preflop/co-open/paint/Raise')
  await page.getByRole('gridcell', { name: 'AA', exact: true }).tap()
  await page.getByRole('gridcell', { name: 'KK', exact: true }).tap()
  await expect(page.getByText('2 hands painted')).toBeVisible()
  await page.getByRole('gridcell', { name: 'KK', exact: true }).tap()
  await expect(page.getByText('1 hands painted')).toBeVisible()
  // A vertical swipe that starts on the grid scrolls the page and paints nothing.
  const box = await page.getByRole('grid', { name: 'Your range' }).boundingBox()
  if (!box) throw new Error('grid not laid out')
  const cdp = await page.context().newCDPSession(page)
  const x = box.x + box.width / 2
  const point = (y: number) => [{ x, y }]
  await cdp.send('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: point(box.y + box.height - 20) })
  for (let step = 1; step <= 10; step += 1) {
    await cdp.send('Input.dispatchTouchEvent', { type: 'touchMove', touchPoints: point(box.y + box.height - 20 - step * 30) })
  }
  await cdp.send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] })
  await expect.poll(() => page.evaluate(() => window.scrollY)).toBeGreaterThan(0)
  await expect(page.getByText('1 hands painted')).toBeVisible()
})

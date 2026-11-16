import { expect, test } from '@playwright/test'

test('a preflop drill answer reveals the chart with your hand marked', async ({ page }) => {
  await page.goto('/#/math-lab/preflop-defend')
  await expect(page.getByText(/^Position/)).toBeVisible()
  await page.keyboard.press('1')
  await expect(page.getByRole('grid', { name: 'Chart for this spot' })).toBeVisible()
  await expect(page.locator('[role=gridcell].hl')).toHaveCount(1)
  await expect(page.getByText(/^Source: Baseline chart/)).toBeVisible()
})

test('paint a range by dragging, check it, and see the diff', async ({ page }) => {
  await page.goto('/#/preflop/utg-open/paint/Raise')
  const grid = page.getByRole('grid', { name: 'Your range' })
  await expect(grid).toBeVisible()
  // Drag along the top row from AA to A2s.
  const first = await page.getByRole('gridcell', { name: 'AA', exact: true }).boundingBox()
  const last = await page.getByRole('gridcell', { name: 'A2s', exact: true }).boundingBox()
  if (!first || !last) throw new Error('grid not laid out')
  await page.mouse.move(first.x + first.width / 2, first.y + first.height / 2)
  await page.mouse.down()
  await page.mouse.move(last.x + last.width / 2, last.y + last.height / 2, { steps: 20 })
  await page.mouse.up()
  await expect(page.getByText('13 hands painted')).toBeVisible()
  await page.getByRole('button', { name: 'Check' }).click()
  await expect(page.getByRole('heading', { name: /combos off/ })).toBeVisible()
  await expect(page.locator('[role=gridcell].missed').first()).toBeVisible()
  await page.getByRole('button', { name: 'Try again' }).click()
  await expect(page.getByText('0 hands painted')).toBeVisible()
})

test('chart explorer links to painting and drilling', async ({ page }) => {
  await page.goto('/#/preflop')
  await page.getByRole('link', { name: /^BTN Folded to you on the button/ }).click()
  await expect(page.getByRole('grid', { name: 'BTN chart' })).toBeVisible()
  await expect(page.getByRole('gridcell', { name: 'AA: Raise' })).toBeVisible()
  await page.getByRole('link', { name: 'Paint the Raise range' }).click()
  await expect(page.getByRole('heading', { name: 'Paint the range' })).toBeVisible()
})

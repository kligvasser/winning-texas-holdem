import { expect, test } from '@playwright/test'

test('read a bot range over two streets, carrying the range forward', async ({ page }) => {
  await page.goto('/#/math-lab/hand-reading')
  const lockIn = page.getByRole('button', { name: 'Lock in' })
  await expect(lockIn).toBeEnabled()
  await expect(page.getByRole('list', { name: 'Action so far' })).toBeVisible()
  await expect(page.getByText('169 of 169 hand classes')).toBeVisible()
  for (const name of ['72o', '82o', '92o']) {
    await page.getByRole('gridcell', { name, exact: true }).click()
  }
  await expect(page.getByText('166 of 169 hand classes')).toBeVisible()
  await lockIn.click()
  await expect(page.getByText(/Range match .*best possible/)).toBeVisible()
  await expect(page.getByRole('grid', { name: /real range/ })).toBeVisible()
  await page.getByRole('button', { name: /Next street/ }).click()
  await expect(page.getByText('166 of 169 hand classes')).toBeVisible()
  await expect(lockIn).toBeEnabled()
})

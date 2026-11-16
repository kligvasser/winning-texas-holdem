import { type Page, expect, test } from '@playwright/test'

const OUT = '../docs/images'

async function graded(page: Page) {
  await expect(page.getByRole('heading', { name: /Correct|Not quite/ })).toBeVisible()
}

test('readme screenshots', async ({ page }) => {
  await page.goto('/')
  await page.screenshot({ path: `${OUT}/home.png` })

  await page.goto('/#/today')
  await page.getByRole('button', { name: 'Start session' }).waitFor()
  await page.screenshot({ path: `${OUT}/today.png` })

  await page.goto('/#/stats')
  await page.getByRole('table').waitFor()
  await page.screenshot({ path: `${OUT}/progress.png` })

  await page.goto('/#/preflop')
  await page.getByText('Your weakest spots').waitFor()
  await page.screenshot({ path: `${OUT}/preflop-overview.png`, fullPage: true })

  await page.goto('/#/math-lab/call-or-fold')
  await page.locator('.prompt').waitFor()
  await page.keyboard.press('1')
  await graded(page)
  await page.screenshot({ path: `${OUT}/drill-call-or-fold.png`, fullPage: true })

  await page.goto('/#/math-lab/outs')
  await page.getByLabel('Your answer').fill('8')
  await page.keyboard.press('Enter')
  await graded(page)
  await page.screenshot({ path: `${OUT}/drill-outs.png`, fullPage: true })

  await page.goto('/#/math-lab/preflop-defend')
  await page.locator('.prompt').waitFor()
  await page.keyboard.press('2')
  await graded(page)
  await page.screenshot({ path: `${OUT}/preflop-drill.png`, fullPage: true })

  await page.goto('/#/preflop/bb-vs-btn')
  await page.getByRole('grid').waitFor()
  await page.screenshot({ path: `${OUT}/preflop-chart.png`, fullPage: true })

  await page.goto('/#/preflop/co-open/paint/Raise')
  for (const name of ['AA', 'KK', 'QQ', 'JJ', 'TT', 'AKs', 'AQs', 'AJs', 'KQs', 'AKo', 'AQo', '72o']) {
    await page.getByRole('gridcell', { name, exact: true }).click()
  }
  await page.getByRole('button', { name: 'Check' }).click()
  await page.getByRole('heading', { name: /combos off/ }).waitFor()
  await page.screenshot({ path: `${OUT}/paint-the-range.png`, fullPage: true })

  await page.goto('/#/learn')
  await page.getByRole('heading', { name: 'Curriculum' }).waitFor()
  await page.screenshot({ path: `${OUT}/learn.png` })

  await page.emulateMedia({ colorScheme: 'dark' })
  await page.goto('/#/math-lab/flop-equity')
  await page.getByLabel('Your answer').fill('40')
  await page.keyboard.press('Enter')
  await graded(page)
  await page.screenshot({ path: `${OUT}/dark-mode.png`, fullPage: true })
})

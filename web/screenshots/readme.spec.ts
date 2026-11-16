import { type Page, expect, test } from '@playwright/test'

const OUT = '../docs/images'

async function graded(page: Page) {
  await expect(page.getByRole('heading', { name: /Correct|Not quite/ })).toBeVisible()
}

test('readme screenshots', async ({ page }) => {
  await page.goto('/')
  await page.screenshot({ animations: 'disabled', path: `${OUT}/home.png` })

  await page.goto('/#/today')
  await page.getByRole('button', { name: 'Start session' }).waitFor()
  await page.screenshot({ animations: 'disabled', path: `${OUT}/today.png` })

  await page.goto('/#/stats')
  await page.getByRole('table').waitFor()
  await page.screenshot({ animations: 'disabled', path: `${OUT}/progress.png` })

  await page.goto('/#/preflop')
  await page.getByText('Your weakest spots').waitFor()
  await page.screenshot({ animations: 'disabled', path: `${OUT}/preflop-overview.png`, fullPage: true })

  await page.goto('/#/math-lab/call-or-fold')
  await page.locator('.prompt').waitFor()
  await page.keyboard.press('1')
  await graded(page)
  await page.screenshot({ animations: 'disabled', path: `${OUT}/drill-call-or-fold.png`, fullPage: true })

  await page.goto('/#/math-lab/outs')
  await page.getByLabel('Your answer').fill('8')
  await page.keyboard.press('Enter')
  await graded(page)
  await page.screenshot({ animations: 'disabled', path: `${OUT}/drill-outs.png`, fullPage: true })

  await page.goto('/#/math-lab/preflop-defend')
  await page.locator('.prompt').waitFor()
  await page.keyboard.press('2')
  await graded(page)
  await page.screenshot({ animations: 'disabled', path: `${OUT}/preflop-drill.png`, fullPage: true })

  await page.goto('/#/preflop/bb-vs-btn')
  await page.getByRole('grid').waitFor()
  await page.screenshot({ animations: 'disabled', path: `${OUT}/preflop-chart.png`, fullPage: true })

  await page.goto('/#/preflop/co-open/paint/Raise')
  for (const name of ['AA', 'KK', 'QQ', 'JJ', 'TT', 'AKs', 'AQs', 'AJs', 'KQs', 'AKo', 'AQo', '72o']) {
    await page.getByRole('gridcell', { name, exact: true }).click()
  }
  await page.getByRole('button', { name: 'Check' }).click()
  await page.getByRole('heading', { name: /combos off/ }).waitFor()
  await page.screenshot({ animations: 'disabled', path: `${OUT}/paint-the-range.png`, fullPage: true })

  await page.goto('/#/learn')
  await page.getByRole('heading', { name: 'Curriculum' }).waitFor()
  await page.screenshot({ animations: 'disabled', path: `${OUT}/learn.png` })

  await page.goto('/#/math-lab/preflop-equity')
  await page.getByLabel('Your answer').fill('60')
  await page.keyboard.press('Enter')
  await graded(page)
  await page.screenshot({ animations: 'disabled', path: `${OUT}/closeness-meter.png`, fullPage: true })

  // Starting-hand odds can be answered from the prompt, so the summary shows a good session.
  const DEALT: Record<string, string> = {
    'pocket aces': '0.45',
    'any pocket pair': '5.88',
    'ace-king (suited or not)': '1.21',
    'ace-king suited': '0.3',
    'jacks or better, or ace-king': '3.02',
    'queens or better': '1.36',
    'a suited connector (32s to AKs)': '3.62',
  }
  await page.goto('/#/math-lab/dealt-odds')
  for (let i = 0; i < 6; i += 1) {
    const input = page.getByLabel('Your answer')
    await expect(input).toBeEnabled()
    const prompt = (await page.locator('.prompt').textContent()) ?? ''
    const group = Object.keys(DEALT).find((g) => prompt.includes(`dealt ${g}?`)) ?? 'pocket aces'
    await page.waitForTimeout(400 + i * 150)
    await input.fill(DEALT[group])
    await input.press('Enter')
    await graded(page)
    await page.getByRole('button', { name: /Next/ }).click()
  }
  await page.getByRole('button', { name: 'End session' }).click()
  await page.getByRole('heading', { name: 'Session complete' }).waitFor()
  await page.screenshot({ animations: 'disabled', path: `${OUT}/session-summary.png` })

  await page.goto('/#/math-lab/hand-story')
  await expect(page.locator('.choices button:enabled').first()).toBeVisible()
  await page.keyboard.press('1')
  await page.getByRole('button', { name: /Next street/ }).click()
  await expect(page.locator('.choices button:enabled').first()).toBeVisible()
  await page.keyboard.press('2')
  await graded(page)
  await page.screenshot({ animations: 'disabled', path: `${OUT}/hand-story.png`, fullPage: true })

  await page.goto('/#/speed/preflop-open')
  await page.getByRole('button', { name: /Start/ }).click()
  await expect(page.locator('.choices button:enabled').first()).toBeVisible()
  await page.screenshot({ animations: 'disabled', path: `${OUT}/speed-round.png` })

  await page.goto('/#/play')
  await page.getByRole('button', { name: /Calling station/ }).click()
  await expect(page.getByRole('region', { name: 'Poker table' })).toBeVisible()
  await page.getByRole('checkbox', { name: 'Coach' }).check()
  await expect(page.getByLabel('Coach', { exact: true }).and(page.locator('p'))).toBeVisible()
  await page.screenshot({ animations: 'disabled', path: `${OUT}/play-table.png`, fullPage: true })
  const result = page.getByRole('region', { name: 'Hand result' })
  for (let i = 0; i < 15 && !(await result.isVisible()); i += 1) {
    const ready = page.locator('[aria-label="Your action"] button:enabled')
    await expect.poll(async () => (await result.isVisible()) || (await ready.count()) > 0).toBe(true)
    if (await result.isVisible()) break
    await page.getByRole('button', { name: /^(Call|Check)/ }).first().click()
  }
  await expect(result).toBeVisible()
  await page.screenshot({ animations: 'disabled', path: `${OUT}/play-review.png`, fullPage: true })

  await page.emulateMedia({ colorScheme: 'dark' })
  await page.goto('/#/math-lab/flop-equity')
  await page.getByLabel('Your answer').fill('40')
  await page.keyboard.press('Enter')
  await graded(page)
  await page.screenshot({ animations: 'disabled', path: `${OUT}/dark-mode.png`, fullPage: true })
})

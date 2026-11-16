export function percent(value: number, digits = 0): string {
  return `${(value * 100).toFixed(digits)}%`
}

export function signed(value: number | null, unit = ''): string {
  if (value === null) return '–'
  const rounded = Math.round(value * 10) / 10
  return `${rounded > 0 ? '+' : ''}${rounded}${unit}`
}

export function seconds(ms: number | null): string {
  return ms === null ? '–' : `${(ms / 1000).toFixed(1)}s`
}

export const TIER_NAMES: Record<number, string> = {
  0: 'Mechanics',
  1: 'Core maths',
  2: 'Preflop',
  3: 'Ranges',
  4: 'Postflop',
  5: 'Game theory',
  6: 'Tournaments',
  7: 'Ongoing',
}

export function totals(rows: { attempts: number; correct: number }[]): {
  attempts: number
  correct: number
} {
  return rows.reduce(
    (sum, row) => ({ attempts: sum.attempts + row.attempts, correct: sum.correct + row.correct }),
    { attempts: 0, correct: 0 },
  )
}

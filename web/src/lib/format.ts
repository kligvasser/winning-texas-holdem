export function percent(value: number, digits = 0): string {
  return `${(value * 100).toFixed(digits)}%`
}

export function signed(value: number | null, unit = ''): string {
  if (value === null) return '–'
  const rounded = Math.round(value * 10) / 10
  return `${rounded > 0 ? '+' : ''}${rounded}${unit}`
}

/** "in 10 minutes", "in 3 days", or "now" for times already past. */
export function until(iso: string, now: Date = new Date()): string {
  const minutes = Math.round((new Date(iso).getTime() - now.getTime()) / 60_000)
  if (minutes <= 0) return 'now'
  if (minutes < 60) return `in ${minutes} minute${minutes === 1 ? '' : 's'}`
  const hours = Math.round(minutes / 60)
  if (hours < 24) return `in ${hours} hour${hours === 1 ? '' : 's'}`
  const days = Math.round(hours / 24)
  return `in ${days} day${days === 1 ? '' : 's'}`
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

/** Group items by tier, tiers ascending, keeping each tier's original order. */
export function groupByTier<T extends { tier: number }>(items: T[]): [number, T[]][] {
  const groups = new Map<number, T[]>()
  for (const item of items) groups.set(item.tier, [...(groups.get(item.tier) ?? []), item])
  return [...groups.entries()].sort(([a], [b]) => a - b)
}

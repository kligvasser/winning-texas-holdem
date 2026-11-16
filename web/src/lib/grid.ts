/** The 13x13 starting-hand grid: ace first, pairs on the diagonal, suited above, offsuit below. */

export const GRID_RANKS = 'AKQJT98765432'

export function gridClass(row: number, col: number): string {
  const a = GRID_RANKS[row]
  const b = GRID_RANKS[col]
  if (row === col) return a + b
  return row < col ? `${a}${b}s` : `${b}${a}o`
}

export const ALL_CELLS: { row: number; col: number; cls: string }[] = Array.from(
  { length: 169 },
  (_, i) => {
    const row = Math.floor(i / 13)
    const col = i % 13
    return { row, col, cls: gridClass(row, col) }
  },
)

/** CSS colour token for an action label. */
export function actionColor(action: string): string {
  if (action === 'Fold') return 'var(--act-fold)'
  if (action === 'Call') return 'var(--act-call)'
  return 'var(--act-raise)'
}

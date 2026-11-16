import type { LoggedAction } from './api'

/** Chips to big blinds (1bb = 2 chips). */
export function toBb(chips: number): number {
  return Math.round((chips / 2) * 100) / 100
}

export function chipsFromBb(bb: number): number {
  return Math.round(bb * 2)
}

/** "You raise to 3bb", "Calling station calls 2bb", "You post 0.5bb". */
export function describe(action: LoggedAction, names: [string, string]): string {
  const who = names[action.player]
  const you = action.player === 0
  const verb = (base: string) => (you ? base : `${base}s`)
  switch (action.kind) {
    case 'post':
      return `${who} ${verb('post')} ${toBb(action.amount)}bb`
    case 'fold':
      return `${who} ${verb('fold')}`
    case 'check':
      return `${who} ${verb('check')}`
    case 'call':
      return `${who} ${verb('call')} ${toBb(action.amount)}bb`
    case 'bet':
      return `${who} ${verb('bet')} ${toBb(action.to)}bb`
    default:
      return `${who} ${verb('raise')} to ${toBb(action.to)}bb`
  }
}

/** Bet presets as totals in chips, clamped to the legal range and de-duplicated. */
export function presets(
  pot: number,
  toCall: number,
  currentBet: number,
  min: number,
  max: number,
): { label: string; to: number }[] {
  const afterCall = pot + toCall
  const sized = (share: number) => currentBet + toCall + Math.round(afterCall * share)
  const options = [
    { label: 'Min', to: min },
    { label: '½ pot', to: sized(0.5) },
    { label: '⅔ pot', to: sized(2 / 3) },
    { label: 'Pot', to: sized(1) },
    { label: 'All-in', to: max },
  ]
  // When sizes collapse to the same amount keep the later label, so a capped bet reads "All-in".
  const seen = new Set<number>()
  return options
    .map((o) => ({ ...o, to: Math.min(max, Math.max(min, o.to)) }))
    .reverse()
    .filter((o) => (seen.has(o.to) ? false : (seen.add(o.to), true)))
    .reverse()
}

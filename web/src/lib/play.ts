import type { LoggedAction, TableView } from './api'

/** Chips to big blinds (1bb = 2 chips). */
export function toBb(chips: number): number {
  return Math.round((chips / 2) * 100) / 100
}

export function chipsFromBb(bb: number): number {
  return Math.round(bb * 2)
}

/** "+3bb", "-1.5bb", "0bb". */
export function signedBb(chips: number): string {
  return `${chips > 0 ? '+' : ''}${toBb(chips)}bb`
}

/** "You raise to 3bb", "Rocky calls 2bb", "You post 0.5bb". */
export function describe(action: LoggedAction, names: string[]): string {
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

/** The short shout over a seat: "Fold", "Call 2bb", "Raise 6bb", "All-in 100bb". */
export function shout(action: LoggedAction, allIn: boolean): string {
  if (allIn) return `All-in ${toBb(action.to)}bb`
  switch (action.kind) {
    case 'post':
      return `Blind ${toBb(action.amount)}bb`
    case 'fold':
      return 'Fold'
    case 'check':
      return 'Check'
    case 'call':
      return `Call ${toBb(action.amount)}bb`
    case 'bet':
      return `Bet ${toBb(action.to)}bb`
    default:
      return `Raise ${toBb(action.to)}bb`
  }
}

const CHIPS: [number, string][] = [
  [200, 'black'],
  [50, 'green'],
  [10, 'blue'],
  [2, 'red'],
  [1, 'white'],
]

/** An amount as a pile of chips, biggest first: 100bb black, 25bb green, 5bb blue, 1bb red, ½bb white. */
export function chipStack(chips: number, max = 12): string[] {
  const pile: string[] = []
  let left = Math.round(chips)
  for (const [value, color] of CHIPS) {
    while (left >= value && pile.length < max) {
      pile.push(color)
      left -= value
    }
  }
  return pile
}

/** How long to show a frame before the next one, in ms: folds and checks pass quickly. */
export function frameDelay(frame: TableView, pace: number, watching: boolean): number {
  const kind = frame.last.kind
  const weight = kind === 'fold' ? 0.5 : kind === 'check' || kind === 'post' ? 0.7 : 1
  return Math.round(pace * weight * (watching ? 0.5 : 1))
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

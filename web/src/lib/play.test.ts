import { describe as group, expect, it } from 'vitest'
import { chipsFromBb, describe, presets, toBb } from './play'

const names: [string, string] = ['You', 'Maniac']
const action = (player: number, kind: string, amount = 0, to = 0) => ({
  street: 'preflop',
  player,
  kind,
  amount,
  to,
  pot: 0,
  to_call: 0,
})

group('play helpers', () => {
  it('converts between chips and big blinds', () => {
    expect(toBb(5)).toBe(2.5)
    expect(chipsFromBb(2.5)).toBe(5)
  })

  it('describes actions in plain words', () => {
    expect(describe(action(0, 'post', 1, 1), names)).toBe('You post 0.5bb')
    expect(describe(action(1, 'post', 2, 2), names)).toBe('Maniac posts 1bb')
    expect(describe(action(0, 'fold'), names)).toBe('You fold')
    expect(describe(action(1, 'check'), names)).toBe('Maniac checks')
    expect(describe(action(0, 'call', 4, 6), names)).toBe('You call 2bb')
    expect(describe(action(1, 'bet', 10, 10), names)).toBe('Maniac bets 5bb')
    expect(describe(action(0, 'raise', 18, 20), names)).toBe('You raise to 10bb')
  })

  it('builds clamped, distinct bet presets', () => {
    const options = presets(20, 0, 0, 2, 200)
    expect(options.map((o) => o.label)).toEqual(['Min', '½ pot', '⅔ pot', 'Pot', 'All-in'])
    expect(options.map((o) => o.to)).toEqual([2, 10, 13, 20, 200])
    // Facing a bet of 10 into 20: a pot raise is call 10 plus the 40 now in the middle.
    expect(presets(30, 10, 0, 20, 200).find((o) => o.label === 'Pot')?.to).toBe(50)
    // A short stack collapses presets into all-in.
    expect(presets(20, 0, 0, 2, 8).map((o) => o.label)).toEqual(['Min', 'All-in'])
  })
})

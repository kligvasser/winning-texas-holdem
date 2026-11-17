import { describe as group, expect, it } from 'vitest'
import { frame } from '../test/fixtures'
import { chipStack, chipsFromBb, describe, frameDelay, presets, shout, signedBb, toBb } from './play'

const names = ['You', 'Maniac']
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
    expect([signedBb(6), signedBb(-3), signedBb(0)]).toEqual(['+3bb', '-1.5bb', '0bb'])
  })

  it('shouts each action in a word or two', () => {
    expect(shout(action(1, 'post', 2, 2), false)).toBe('Blind 1bb')
    expect(shout(action(1, 'fold'), false)).toBe('Fold')
    expect(shout(action(1, 'check'), false)).toBe('Check')
    expect(shout(action(1, 'call', 4, 6), false)).toBe('Call 2bb')
    expect(shout(action(1, 'bet', 10, 10), false)).toBe('Bet 5bb')
    expect(shout(action(1, 'raise', 18, 20), false)).toBe('Raise 10bb')
    expect(shout(action(1, 'raise', 200, 200), true)).toBe('All-in 100bb')
  })

  it('turns an amount into a pile of chips', () => {
    expect(chipStack(0)).toEqual([])
    expect(chipStack(75)).toEqual(['green', 'blue', 'blue', 'red', 'red', 'white'])
    expect(chipStack(400)).toEqual(['black', 'black'])
    expect(chipStack(9, 3)).toEqual(['red', 'red', 'red'])
  })

  it('paces folds and checks faster than bets, and faster still once you are out', () => {
    const on = (kind: string) => frame({ last: action(1, kind) })
    expect(frameDelay(on('raise'), 700, false)).toBe(700)
    expect(frameDelay(on('check'), 700, false)).toBe(490)
    expect(frameDelay(on('post'), 700, false)).toBe(490)
    expect(frameDelay(on('fold'), 700, false)).toBe(350)
    expect(frameDelay(on('call'), 700, true)).toBe(350)
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

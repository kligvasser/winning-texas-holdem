import { describe, expect, it } from 'vitest'
import { EXTRA_TITLES, TIER_NAMES, fixed, groupByTier, percent, seconds, signed, totals, until } from './format'

describe('format', () => {
  it('formats percentages', () => {
    expect(percent(0.756)).toBe('76%')
    expect(percent(0.756, 1)).toBe('75.6%')
  })

  it('formats signed values', () => {
    expect(signed(null)).toBe('–')
    expect(signed(2.34, ' pts')).toBe('+2.3 pts')
    expect(signed(-1.26)).toBe('-1.3')
    expect(signed(0)).toBe('0')
  })

  it('formats fixed decimals', () => {
    expect(fixed(null)).toBe('–')
    expect(fixed(46.325)).toBe('46.3')
    expect(EXTRA_TITLES['preflop-paint']).toBe('Paint the range')
  })

  it('formats seconds', () => {
    expect(seconds(null)).toBe('–')
    expect(seconds(2500)).toBe('2.5s')
  })

  it('names every tier', () => {
    expect(Object.keys(TIER_NAMES)).toHaveLength(8)
  })
})

describe('until', () => {
  const now = new Date('2026-11-16T12:00:00Z')
  it.each([
    ['2026-11-16T11:00:00Z', 'now'],
    ['2026-11-16T12:01:00Z', 'in 1 minute'],
    ['2026-11-16T12:10:00Z', 'in 10 minutes'],
    ['2026-11-16T13:00:00Z', 'in 1 hour'],
    ['2026-11-16T17:00:00Z', 'in 5 hours'],
    ['2026-11-17T12:00:00Z', 'in 1 day'],
    ['2026-11-19T12:00:00Z', 'in 3 days'],
  ])('%s is %s', (iso, text) => {
    expect(until(iso, now)).toBe(text)
  })

  it('defaults to the current time', () => {
    expect(until(new Date(Date.now() + 2 * 86_400_000).toISOString())).toBe('in 2 days')
  })
})

describe('totals', () => {
  it('sums attempts and correct answers', () => {
    expect(totals([])).toEqual({ attempts: 0, correct: 0 })
    expect(totals([{ attempts: 3, correct: 1 }, { attempts: 2, correct: 2 }])).toEqual({ attempts: 5, correct: 3 })
  })
})

describe('groupByTier', () => {
  it('groups in ascending tier order, keeping order within a tier', () => {
    const items = [{ tier: 2, k: 'a' }, { tier: 0, k: 'b' }, { tier: 2, k: 'c' }]
    expect(groupByTier(items)).toEqual([
      [0, [{ tier: 0, k: 'b' }]],
      [2, [{ tier: 2, k: 'a' }, { tier: 2, k: 'c' }]],
    ])
    expect(groupByTier([])).toEqual([])
  })
})

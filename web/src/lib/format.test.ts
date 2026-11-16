import { describe, expect, it } from 'vitest'
import { TIER_NAMES, percent, seconds, signed, totals } from './format'

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

  it('formats seconds', () => {
    expect(seconds(null)).toBe('–')
    expect(seconds(2500)).toBe('2.5s')
  })

  it('names every tier', () => {
    expect(Object.keys(TIER_NAMES)).toHaveLength(8)
  })
})

describe('totals', () => {
  it('sums attempts and correct answers', () => {
    expect(totals([])).toEqual({ attempts: 0, correct: 0 })
    expect(totals([{ attempts: 3, correct: 1 }, { attempts: 2, correct: 2 }])).toEqual({ attempts: 5, correct: 3 })
  })
})

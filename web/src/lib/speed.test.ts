import { afterEach, describe, expect, it } from 'vitest'
import { loadBest, saveBest } from './speed'

afterEach(() => localStorage.clear())

describe('speed round bests', () => {
  it('keeps the highest score per round', () => {
    expect(loadBest('mixed')).toBe(0)
    expect(saveBest('mixed', 7)).toBe(true)
    expect(saveBest('mixed', 5)).toBe(false)
    expect(saveBest('mixed', 7)).toBe(false)
    expect(loadBest('mixed')).toBe(7)
    expect(loadBest('nuts')).toBe(0)
  })

  it('copes with storage that is unavailable', () => {
    const broken = {
      getItem: () => {
        throw new Error('denied')
      },
      setItem: () => {
        throw new Error('denied')
      },
    } as unknown as Storage
    expect(loadBest('mixed', broken)).toBe(0)
    expect(saveBest('mixed', 3, broken)).toBe(true)
  })
})

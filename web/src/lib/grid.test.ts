import { describe, expect, it } from 'vitest'
import { ALL_CELLS, actionColor, classCombos, gridClass } from './grid'

describe('grid', () => {
  it('lays out pairs, suited and offsuit hands', () => {
    expect(gridClass(0, 0)).toBe('AA')
    expect(gridClass(0, 1)).toBe('AKs')
    expect(gridClass(1, 0)).toBe('AKo')
    expect(gridClass(12, 12)).toBe('22')
    expect(gridClass(11, 12)).toBe('32s')
  })

  it('has 169 distinct cells', () => {
    expect(new Set(ALL_CELLS.map((c) => c.cls)).size).toBe(169)
    expect(ALL_CELLS[14]).toEqual({ row: 1, col: 1, cls: 'KK' })
  })

  it('colours actions', () => {
    expect(actionColor('Fold')).toBe('var(--act-fold)')
    expect(actionColor('Call')).toBe('var(--act-call)')
    expect(actionColor('Raise')).toBe('var(--act-raise)')
    expect(actionColor('3-bet')).toBe('var(--act-raise)')
  })
})

describe('classCombos', () => {
  it('counts combos per class', () => {
    expect(classCombos('AA')).toBe(6)
    expect(classCombos('AKs')).toBe(4)
    expect(classCombos('AKo')).toBe(12)
  })
})

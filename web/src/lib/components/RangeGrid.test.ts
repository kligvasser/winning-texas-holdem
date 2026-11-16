import { fireEvent, render, screen } from '@testing-library/svelte'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { utgGrid } from '../../test/fixtures'
import ActionLegend from './ActionLegend.svelte'
import RangeGrid from './RangeGrid.svelte'

const cell = (name: string | RegExp) => screen.getByRole('gridcell', { name })

/** jsdom has no layout, so stub the hit test the drag handler relies on. */
function pointAt(element: Element | null) {
  document.elementFromPoint = () => element
}

afterEach(() => vi.restoreAllMocks())

describe('RangeGrid display mode', () => {
  it('colours cells by action and outlines the highlighted hand', () => {
    render(RangeGrid, { grid: utgGrid, highlight: 'AKs', label: 'UTG chart' })
    expect(screen.getByRole('grid', { name: 'UTG chart' })).toBeInTheDocument()
    expect(screen.getAllByRole('gridcell')).toHaveLength(169)
    expect(cell('AA: Raise')).toHaveAttribute('aria-selected', 'true')
    expect(cell('AKs: Raise')).toHaveClass('hl')
    expect(cell('72o: Fold')).toHaveAttribute('aria-selected', 'false')
    expect(cell('72o: Fold')).toHaveAttribute('tabindex', '-1')
  })

  it('ignores pointer and keyboard input', async () => {
    render(RangeGrid, { grid: utgGrid })
    await fireEvent.pointerDown(cell('AA: Raise'))
    await fireEvent.click(cell('AA: Raise'), { detail: 0 })
    await fireEvent.pointerMove(screen.getByRole('grid'))
    expect(cell('AA: Raise')).toHaveAttribute('aria-selected', 'true')
  })
})

describe('RangeGrid paint mode', () => {
  it('paints by pointer, dragging with the same value', async () => {
    const onpaint = vi.fn()
    const { rerender } = render(RangeGrid, { painted: [], onpaint })
    expect(screen.getByRole('grid')).toHaveClass('paint')
    await fireEvent.pointerDown(cell('AA'))
    expect(onpaint).toHaveBeenLastCalledWith(['AA'])
    await rerender({ painted: ['AA'], onpaint })
    // Drag over KK (paint) and back over AA (already painted, no change).
    pointAt(cell('KK'))
    await fireEvent.pointerMove(screen.getByRole('grid'))
    expect(onpaint).toHaveBeenLastCalledWith(['AA', 'KK'])
    await rerender({ painted: ['AA', 'KK'], onpaint })
    pointAt(cell('AA'))
    await fireEvent.pointerMove(screen.getByRole('grid'))
    expect(onpaint).toHaveBeenCalledTimes(2)
    // Moving over something that is not a cell does nothing.
    pointAt(screen.getByRole('grid'))
    await fireEvent.pointerMove(screen.getByRole('grid'))
    pointAt(null)
    await fireEvent.pointerMove(screen.getByRole('grid'))
    expect(onpaint).toHaveBeenCalledTimes(2)
    // After releasing, moves no longer paint.
    await fireEvent.pointerUp(window)
    await fireEvent.pointerMove(screen.getByRole('grid'))
    expect(onpaint).toHaveBeenCalledTimes(2)
  })

  it('fills every cell along a fast drag', async () => {
    const onpaint = vi.fn()
    render(RangeGrid, { painted: [], onpaint })
    await fireEvent.pointerDown(cell('AA'))
    pointAt(cell('A2s'))
    await fireEvent.pointerMove(screen.getByRole('grid'))
    const painted = onpaint.mock.lastCall?.[0] as string[]
    expect(painted).toEqual(expect.arrayContaining(['AKs', 'AQs', 'A7s', 'A3s', 'A2s']))
    expect(painted).toHaveLength(13) // the whole top row, AA to A2s
    await fireEvent.pointerUp(window)
  })

  it('toggles on tap for touch and leaves swipes to scroll', async () => {
    const onpaint = vi.fn()
    render(RangeGrid, { painted: [], onpaint })
    await fireEvent.pointerDown(cell('QQ'), { pointerType: 'touch' })
    expect(onpaint).not.toHaveBeenCalled()
    const tap = new MouseEvent('click', { bubbles: true, detail: 1 })
    Object.defineProperty(tap, 'pointerType', { value: 'touch' })
    cell('QQ').dispatchEvent(tap)
    expect(onpaint).toHaveBeenLastCalledWith(['QQ'])
  })

  it('moves focus with the arrow keys and stays inside the grid', async () => {
    render(RangeGrid, { painted: [], onpaint: vi.fn() })
    const aa = cell('AA')
    expect(aa).toHaveAttribute('tabindex', '0')
    expect(cell('KK')).toHaveAttribute('tabindex', '-1')
    aa.focus()
    await fireEvent.keyDown(aa, { key: 'ArrowRight' })
    expect(cell('AKs')).toHaveFocus()
    await fireEvent.keyDown(cell('AKs'), { key: 'ArrowDown' })
    expect(cell('KK')).toHaveFocus()
    expect(cell('KK')).toHaveAttribute('tabindex', '0')
    await fireEvent.keyDown(cell('KK'), { key: 'ArrowUp' })
    await fireEvent.keyDown(cell('AKs'), { key: 'ArrowLeft' })
    expect(cell('AA')).toHaveFocus()
    // Edges: no wrapping and no leaving the grid.
    await fireEvent.keyDown(cell('AA'), { key: 'ArrowLeft' })
    await fireEvent.keyDown(cell('AA'), { key: 'ArrowUp' })
    expect(cell('AA')).toHaveFocus()
    cell('A2s').focus()
    await fireEvent.keyDown(cell('A2s'), { key: 'ArrowRight' })
    expect(cell('A2s')).toHaveFocus()
    cell('22').focus()
    await fireEvent.keyDown(cell('22'), { key: 'ArrowDown' })
    await fireEvent.keyDown(cell('22'), { key: 'Tab' })
    expect(cell('22')).toHaveFocus()
  })

  it('paints in the colour of the chosen action', () => {
    render(RangeGrid, { painted: ['AA'], onpaint: vi.fn(), paintAction: 'Call' })
    expect(cell('AA').style.background).toBe('var(--act-call)')
  })

  it('erases when the drag starts on a painted cell', async () => {
    const onpaint = vi.fn()
    render(RangeGrid, { painted: ['AA', 'KK'], onpaint })
    await fireEvent.pointerDown(cell('AA'))
    expect(onpaint).toHaveBeenLastCalledWith(['KK'])
  })

  it('toggles with the keyboard but ignores pointer clicks', async () => {
    const onpaint = vi.fn()
    render(RangeGrid, { painted: [], onpaint })
    expect(cell('AA')).toHaveAttribute('tabindex', '0')
    await fireEvent.click(cell('QQ'), { detail: 1 })
    expect(onpaint).not.toHaveBeenCalled()
    await fireEvent.click(cell('QQ'), { detail: 0 })
    expect(onpaint).toHaveBeenLastCalledWith(['QQ'])
  })

  it('marks missed and extra cells after checking', () => {
    render(RangeGrid, { painted: ['72o'], onpaint: vi.fn(), diff: { missed: ['AA'], extra: ['72o'] } })
    expect(cell('AA')).toHaveClass('missed')
    expect(cell('72o')).toHaveClass('extra')
    expect(cell('72o')).toHaveAttribute('aria-selected', 'true')
  })

  it('shows an empty grid by default', () => {
    render(RangeGrid, {})
    expect(cell('AA')).toHaveAttribute('aria-selected', 'false')
  })
})

describe('ActionLegend', () => {
  it('lists actions with optional frequencies', () => {
    render(ActionLegend, { actions: ['Raise', 'Fold'], frequencies: { Raise: 0.19 } })
    expect(screen.getByText('19%')).toBeInTheDocument()
    expect(screen.getAllByRole('listitem')).toHaveLength(2)
  })

  it('works without frequencies', () => {
    render(ActionLegend, { actions: ['Call'] })
    expect(screen.queryByText(/%/)).toBeNull()
  })
})

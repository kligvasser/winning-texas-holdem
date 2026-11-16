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

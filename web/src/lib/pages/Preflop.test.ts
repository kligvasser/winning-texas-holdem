import { fireEvent, render, screen } from '@testing-library/svelte'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { api } from '../api'
import { leaks, spots } from '../../test/fixtures'
import Preflop from './Preflop.svelte'

vi.mock('../api', () => ({ api: { spots: vi.fn(), leaks: vi.fn(), paint: vi.fn() } }))
const mocked = vi.mocked(api)

beforeEach(() => {
  vi.resetAllMocks()
  mocked.spots.mockResolvedValue(spots)
  mocked.leaks.mockResolvedValue(leaks)
})

describe('Preflop overview', () => {
  it('lists spots by kind and the weakest spots', async () => {
    render(Preflop)
    expect(screen.getByText('Loading…')).toBeInTheDocument()
    expect(await screen.findByRole('heading', { name: 'Opening (folded to you)' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Facing a raise' })).toBeInTheDocument()
    expect(screen.getByText('Plays 19% of hands')).toBeInTheDocument()
    expect(screen.getByRole('rowheader', { name: /UTG: Folded/ })).toBeInTheDocument()
    expect(screen.getByText('A9o')).toBeInTheDocument()
    expect(screen.getByText('–')).toBeInTheDocument()
  })

  it('hides the leak table with no answers yet', async () => {
    mocked.leaks.mockResolvedValue([])
    render(Preflop)
    await screen.findByRole('heading', { name: 'Preflop' })
    expect(screen.queryByText('Your weakest spots')).toBeNull()
  })

  it('reports load failures and unknown spots', async () => {
    const { unmount } = render(Preflop, { params: ['nope'] })
    expect(await screen.findByText(/Unknown spot “nope”/)).toBeInTheDocument()
    unmount()
    mocked.spots.mockRejectedValue(new Error('offline'))
    render(Preflop)
    expect(await screen.findByRole('alert')).toHaveTextContent('Preflop error: offline')
  })
})

describe('Preflop chart', () => {
  it('shows the chart, legend and paint links', async () => {
    render(Preflop, { params: ['bb-vs-btn'] })
    expect(await screen.findByRole('grid', { name: 'BB chart' })).toBeInTheDocument()
    expect(screen.getByText('Defend wide.')).toBeInTheDocument()
    expect(screen.getByText('44%')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Paint the 3-bet range' })).toHaveAttribute('href', '#/preflop/bb-vs-btn/paint/3-bet')
    expect(screen.getByRole('link', { name: 'Drill these spots' })).toHaveAttribute('href', '#/math-lab/preflop-defend')
  })

  it('links opening spots to the opening drill and ignores bad paint actions', async () => {
    render(Preflop, { params: ['utg-open', 'paint', 'Fold'] })
    expect(await screen.findByRole('link', { name: 'Drill these spots' })).toHaveAttribute('href', '#/math-lab/preflop-open')
  })
})

describe('Paint the range', () => {
  it('paints, checks, shows the diff and resets', async () => {
    mocked.paint.mockResolvedValue({ correct: ['AA'], missed: ['AKs'], extra: ['72o'], combos_wrong: 16, accuracy: 0.988 })
    render(Preflop, { params: ['utg-open', 'paint', 'Raise'] })
    expect(await screen.findByRole('heading', { name: 'Paint the range' })).toBeInTheDocument()
    await fireEvent.pointerDown(screen.getByRole('gridcell', { name: 'AA' }))
    await fireEvent.pointerUp(window)
    await fireEvent.pointerDown(screen.getByRole('gridcell', { name: '72o' }))
    expect(screen.getByText('2 hands painted')).toBeInTheDocument()
    await fireEvent.click(screen.getByRole('button', { name: 'Check' }))
    expect(mocked.paint).toHaveBeenCalledWith('utg-open', 'Raise', ['AA', '72o'])
    expect(await screen.findByRole('heading', { name: '16 combos off' })).toBeInTheDocument()
    expect(screen.getByText('98.8% of all combos classified correctly.', { exact: false })).toBeInTheDocument()
    expect(screen.getByRole('gridcell', { name: 'AKs' })).toHaveClass('missed')
    await fireEvent.click(screen.getByRole('button', { name: 'Try again' }))
    expect(screen.getByText('0 hands painted')).toBeInTheDocument()
  })

  it('celebrates a perfect range and can clear', async () => {
    mocked.paint.mockResolvedValue({ correct: ['AA'], missed: [], extra: [], combos_wrong: 0, accuracy: 1 })
    render(Preflop, { params: ['utg-open', 'paint', 'Raise'] })
    await fireEvent.pointerDown(await screen.findByRole('gridcell', { name: 'AA' }))
    await fireEvent.click(screen.getByRole('button', { name: 'Clear' }))
    expect(screen.getByText('0 hands painted')).toBeInTheDocument()
    await fireEvent.click(screen.getByRole('button', { name: 'Check' }))
    expect(await screen.findByRole('heading', { name: 'Perfect' })).toBeInTheDocument()
    expect(screen.queryByText('Missed:')).toBeNull()
  })

  it('reports check failures', async () => {
    mocked.paint.mockRejectedValue(new Error('bad action'))
    render(Preflop, { params: ['utg-open', 'paint', 'Raise'] })
    await fireEvent.click(await screen.findByRole('button', { name: 'Check' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Preflop error: bad action')
  })
})

import { render, screen } from '@testing-library/svelte'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { api } from '../api'
import { drills, numberQuestion, stats } from '../../test/fixtures'
import Home from './Home.svelte'
import MathLab from './MathLab.svelte'
import Stats from './Stats.svelte'

vi.mock('../api', () => ({
  api: { drills: vi.fn(), stats: vi.fn(), question: vi.fn(), answer: vi.fn() },
}))
const mocked = vi.mocked(api)

beforeEach(() => {
  vi.resetAllMocks()
  mocked.drills.mockResolvedValue(drills)
  mocked.question.mockResolvedValue(numberQuestion)
})

describe('Home', () => {
  it('links to the main areas', () => {
    render(Home)
    expect(screen.getByRole('heading', { name: "Winning Texas Hold'em" })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Math Lab/ })).toHaveAttribute('href', '#/math-lab')
    expect(screen.getByRole('link', { name: 'Start a mixed session' })).toHaveAttribute('href', '#/math-lab/mixed')
  })
})

describe('MathLab', () => {
  it('lists drills grouped by tier', async () => {
    render(MathLab)
    expect(await screen.findByText('Tier 0 · Mechanics')).toBeInTheDocument()
    const headings = screen.getAllByRole('heading', { level: 2 }).map((h) => h.textContent)
    expect(headings).toEqual(['Tier 0 · Mechanics', 'Tier 1 · Core maths'])
    expect(screen.getByRole('link', { name: /Pot odds/ })).toHaveAttribute('href', '#/math-lab/pot-odds')
  })

  it('runs one drill', async () => {
    render(MathLab, { selected: 'pot-odds' })
    expect(await screen.findByLabelText('Your answer')).toBeInTheDocument()
    expect(mocked.question).toHaveBeenCalledWith('pot-odds')
    expect(screen.getByRole('link', { name: /All drills/ })).toBeInTheDocument()
  })

  it('runs a mixed session', async () => {
    render(MathLab, { selected: 'mixed' })
    expect(await screen.findByLabelText('Your answer')).toBeInTheDocument()
  })

  it('reports unknown drills once the list has loaded', async () => {
    render(MathLab, { selected: 'nope' })
    expect(await screen.findByText('Unknown drill “nope”.')).toBeInTheDocument()
  })

  it('reports load failures', async () => {
    mocked.drills.mockRejectedValue(new Error('offline'))
    render(MathLab)
    expect(await screen.findByRole('alert')).toHaveTextContent('Could not load drills: offline')
  })
})

describe('Stats', () => {
  it('shows a table with bias colouring and totals', async () => {
    mocked.stats.mockResolvedValue(stats)
    render(Stats)
    expect(screen.getByText('Loading…')).toBeInTheDocument()
    expect(await screen.findByText('8 answers, 75% correct.')).toBeInTheDocument()
    expect(screen.getByRole('rowheader', { name: 'Pot odds' })).toBeInTheDocument()
    expect(screen.getByRole('rowheader', { name: 'retired' })).toBeInTheDocument()
    expect(screen.getByText('+1.5')).toHaveClass('over')
    expect(screen.getByText('-1')).toHaveClass('under')
    expect(screen.getByText('2.5s')).toBeInTheDocument()
  })

  it('shows an empty state', async () => {
    mocked.stats.mockResolvedValue([])
    render(Stats)
    expect(await screen.findByText(/No answers yet/)).toBeInTheDocument()
  })

  it('reports load failures', async () => {
    mocked.stats.mockRejectedValue(new Error('offline'))
    render(Stats)
    expect(await screen.findByRole('alert')).toHaveTextContent('Could not load stats: offline')
  })
})

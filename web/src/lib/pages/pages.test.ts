import { fireEvent, render, screen } from '@testing-library/svelte'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { api } from '../api'
import { curriculum, drills, numberQuestion, plan, stats } from '../../test/fixtures'
import Home from './Home.svelte'
import Learn from './Learn.svelte'
import MathLab from './MathLab.svelte'
import Stats from './Stats.svelte'
import Today from './Today.svelte'

vi.mock('../api', () => ({
  api: {
    drills: vi.fn(),
    stats: vi.fn(),
    question: vi.fn(),
    answer: vi.fn(),
    today: vi.fn(),
    curriculum: vi.fn(),
  },
}))
const mocked = vi.mocked(api)

beforeEach(() => {
  vi.resetAllMocks()
  mocked.drills.mockResolvedValue(drills)
  mocked.question.mockResolvedValue(numberQuestion)
  mocked.today.mockResolvedValue(plan)
  mocked.curriculum.mockResolvedValue(curriculum)
})

describe('Home', () => {
  it('links to the main areas', () => {
    render(Home)
    expect(screen.getByRole('heading', { name: "Winning Texas Hold'em" })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Math Lab/ })).toHaveAttribute('href', '#/math-lab')
    expect(screen.getByRole('link', { name: /^Learn/ })).toHaveAttribute('href', '#/learn')
    expect(screen.getByRole('link', { name: /^Preflop/ })).toHaveAttribute('href', '#/preflop')
    expect(screen.getByRole('link', { name: "Today's session" })).toHaveAttribute('href', '#/today')
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
    expect(screen.getByText('2.0')).toBeInTheDocument()
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

describe('Today', () => {
  it('summarises the plan and runs the queue', async () => {
    render(Today)
    expect(screen.getByText('Loading…')).toBeInTheDocument()
    expect(await screen.findByText('Due for review')).toBeInTheDocument()
    expect(screen.getByText('New today')).toBeInTheDocument()
    expect(screen.queryByText(/Extra practice/)).toBeNull()
    expect(screen.getByText('Pot odds')).toBeInTheDocument()
    await fireEvent.click(screen.getByRole('button', { name: 'Start session' }))
    expect(await screen.findByRole('progressbar')).toBeInTheDocument()
    expect(mocked.question).toHaveBeenCalledWith('pot-odds')
  })

  it('shows extra practice and falls back to keys for unknown titles', async () => {
    mocked.today.mockResolvedValue({ due: [], new: [], extra: ['mystery'], queue: ['mystery'] })
    render(Today)
    expect(await screen.findByText('Extra practice: lowest recall')).toBeInTheDocument()
    expect(screen.getByText('mystery')).toBeInTheDocument()
  })

  it('says when nothing is due', async () => {
    mocked.today.mockResolvedValue({ due: [], new: [], extra: [], queue: [] })
    render(Today)
    expect(await screen.findByText(/Nothing is due/)).toBeInTheDocument()
  })

  it('reports load failures', async () => {
    mocked.today.mockRejectedValue(new Error('offline'))
    render(Today)
    expect(await screen.findByRole('alert')).toHaveTextContent("Could not load today's session: offline")
  })
})

describe('Learn', () => {
  it('lists concepts by tier with status and mastery', async () => {
    render(Learn)
    expect(screen.getByText('Loading…')).toBeInTheDocument()
    expect(await screen.findByRole('heading', { name: 'Curriculum' })).toBeInTheDocument()
    const tiers = screen.getAllByRole('heading', { level: 2 }).map((h) => h.textContent)
    expect(tiers).toEqual(['Tier 0 · Mechanics', 'Tier 1 · Core maths', 'Tier 6 · Tournaments', 'Course materials'])
    expect(screen.getByRole('link', { name: /Reading the board/ })).toHaveClass('status-mastered')
    expect(screen.getByLabelText('Mastery 90%')).toBeInTheDocument()
    expect(screen.queryByLabelText(/Mastery 50%/)).toBeNull()
    expect(screen.getByRole('link', { name: '2016 lecture slides' })).toHaveAttribute('target', '_blank')
  })

  it('shows a concept with drills, prerequisites and lectures', async () => {
    render(Learn, { selected: 'pot-odds' })
    expect(await screen.findByRole('heading', { name: 'Pot odds and EV' })).toBeInTheDocument()
    expect(screen.getByText('Tier 1 · Core maths')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Pot odds' })).toHaveAttribute('href', '#/math-lab/pot-odds')
    expect(screen.getByRole('link', { name: 'unlisted' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Reading the board' })).toHaveAttribute('href', '#/learn/board-reading')
    expect(screen.getByRole('link', { name: 'ghost' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: '2016 L1 · Overview' })).toHaveAttribute('rel', 'noreferrer')
  })

  it('handles concepts without drills or prerequisites', async () => {
    render(Learn, { selected: 'icm' })
    expect(await screen.findByText(/arrive in a later milestone/)).toBeInTheDocument()
    expect(screen.queryByText('Builds on')).toBeNull()
  })

  it('reports unknown concepts and load failures', async () => {
    const { unmount } = render(Learn, { selected: 'nope' })
    expect(await screen.findByText(/Unknown concept “nope”/)).toBeInTheDocument()
    unmount()
    mocked.curriculum.mockRejectedValue(new Error('offline'))
    render(Learn)
    expect(await screen.findByRole('alert')).toHaveTextContent('Could not load the curriculum: offline')
  })
})

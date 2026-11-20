import { fireEvent, render, screen } from '@testing-library/svelte'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { api } from '../api'
import { activity, correctResult, curriculum, drills, numberQuestion, plan, stats } from '../../test/fixtures'
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
    activity: vi.fn(),
  },
}))
const mocked = vi.mocked(api)

beforeEach(() => {
  vi.resetAllMocks()
  mocked.drills.mockResolvedValue(drills)
  mocked.question.mockResolvedValue(numberQuestion)
  mocked.today.mockResolvedValue(plan)
  mocked.curriculum.mockResolvedValue(curriculum)
  mocked.activity.mockResolvedValue(activity)
})

describe('Home', () => {
  it('links to the main areas', () => {
    mocked.activity.mockReturnValue(new Promise(() => {}))
    render(Home)
    expect(screen.getByRole('heading', { name: "Winning Texas Hold'em" })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Math Lab/ })).toHaveAttribute('href', '#/math-lab')
    expect(screen.getByRole('link', { name: /Learn/ })).toHaveAttribute('href', '#/learn')
    expect(screen.getByRole('link', { name: /Preflop/ })).toHaveAttribute('href', '#/preflop')
    expect(screen.getByRole('link', { name: /Play/ })).toHaveAttribute('href', '#/play')
    expect(screen.getByRole('link', { name: "Today's session" })).toHaveAttribute('href', '#/today')
    expect(screen.getByText('Welcome! Start with a short session.')).toBeInTheDocument()
  })

  it('shows the dashboard with streak, goal and due drills', async () => {
    render(Home)
    expect(await screen.findByRole('figure', { name: 'Answers today: 8 of 20' })).toBeInTheDocument()
    expect(screen.getByText('🔥 4')).not.toHaveClass('cold')
    expect(screen.getByText('day streak · best 6')).toBeInTheDocument()
    expect(screen.getByText('144')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: "Start today's session · 2 questions" })).toBeInTheDocument()
    expect(screen.getByText('Good to see you back. Keep the streak going.')).toBeInTheDocument()
  })

  it.each([
    [{ answered_today: 25 }, 'Daily goal done. Nice work.'],
    [{ answered_today: 0, practiced_today: false }, "Your 4-day streak is waiting for today's session."],
    [{ answered_today: 0, practiced_today: false, streak: 0 }, 'Welcome back. A short session gets you rolling again.'],
    [{ total: 0 }, 'Welcome! Start with a short session.'],
  ])('greets %j', async (over, text) => {
    mocked.activity.mockResolvedValue({ ...activity, ...over })
    mocked.today.mockResolvedValue({ due: [], new: [], extra: [], queue: [] })
    render(Home)
    expect(await screen.findByText(text)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: "Today's session" })).toBeInTheDocument()
  })

  it('greys out the flame until you practise today', async () => {
    mocked.activity.mockResolvedValue({ ...activity, practiced_today: false })
    render(Home)
    expect(await screen.findByText('🔥 4')).toHaveClass('cold')
  })

  it('still works when the dashboard cannot load', async () => {
    mocked.activity.mockRejectedValue(new Error('offline'))
    render(Home)
    await Promise.resolve()
    expect(screen.queryByRole('region', { name: 'Your practice' })).toBeNull()
    expect(screen.getByRole('link', { name: /Math Lab/ })).toBeInTheDocument()
  })
})

describe('MathLab', () => {
  it('lists drills grouped by tier', async () => {
    mocked.drills.mockResolvedValue(drills.map((d) => ({ ...d, speed: d.key === 'showdown' })))
    render(MathLab)
    expect(await screen.findByText('Tier 0 · Mechanics')).toBeInTheDocument()
    const headings = screen.getAllByRole('heading', { level: 2 }).map((h) => h.textContent)
    expect(headings).toEqual(['Tier 0 · Mechanics', 'Tier 1 · Core maths'])
    expect(screen.getByRole('link', { name: /Pot odds/ })).toHaveAttribute('href', '#/math-lab/pot-odds')
    expect(screen.getByTitle('Has a speed round')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /speed round/ })).toHaveAttribute('href', '#/speed/mixed')
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
    expect(screen.getByText('Loading…')).toBeInTheDocument()
    expect(await screen.findByText('Unknown drill “nope”.')).toBeInTheDocument()
  })

  it('reports load failures', async () => {
    mocked.drills.mockRejectedValue(new Error('offline'))
    render(MathLab)
    expect(await screen.findByRole('alert')).toHaveTextContent('Could not load drills: offline')
  })
})

describe('Stats', () => {
  it('shows tiles, the heatmap and drills sorted weakest first', async () => {
    mocked.stats.mockResolvedValue([...stats, { drill: 'preflop-paint', attempts: 1, correct: 0, accuracy: 0, mean_abs_error: 324, bias: 324, mean_ms: null }])
    render(Stats)
    expect(screen.getByText('Loading…')).toBeInTheDocument()
    expect(await screen.findByText('🔥 4')).toBeInTheDocument()
    expect(screen.getByText('9')).toBeInTheDocument() // answers across all drills
    expect(screen.getByRole('img', { name: /Practised on 2 of the last 3 days/ })).toBeInTheDocument()
    const rows = screen.getAllByRole('rowheader').map((r) => r.textContent)
    expect(rows).toEqual(['Paint the range', 'Who wins?', 'Pot odds', 'retired'])
    expect(screen.getByRole('link', { name: 'Paint the range' })).toHaveAttribute('href', '#/preflop')
    expect(screen.getByRole('link', { name: 'Pot odds' })).toHaveAttribute('href', '#/math-lab/pot-odds')
    expect(screen.getByText('+1.5')).toHaveClass('over')
    expect(screen.getByText('-1')).toHaveClass('under')
    expect(screen.getByText('2.5s')).toBeInTheDocument()
    expect(screen.getByText('2.0')).toBeInTheDocument()
    const bars = document.querySelectorAll('.bar span')
    expect(bars[0]).toHaveClass('weak')
    expect(bars[3]).toHaveClass('good')
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

  it('loads again when asked to try again', async () => {
    mocked.stats.mockRejectedValueOnce(new Error('offline')).mockResolvedValue(stats)
    mocked.activity.mockResolvedValue(activity)
    render(Stats)
    await fireEvent.click(await screen.findByRole('button', { name: 'Try again' }))
    expect(await screen.findByRole('table')).toBeInTheDocument()
    expect(screen.queryByRole('alert')).toBeNull()
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

  it('saves progress, offers to resume after leaving, and can start over', async () => {
    sessionStorage.clear()
    mocked.answer.mockResolvedValue({ ...correctResult })
    const user = userEvent.setup()
    const first = render(Today, { day: '2026-11-16' })
    await fireEvent.click(await screen.findByRole('button', { name: 'Start session' }))
    await user.type(await screen.findByLabelText('Your answer'), '25{Enter}')
    await screen.findByRole('button', { name: /Next/ })
    first.unmount()

    const second = render(Today, { day: '2026-11-16' })
    expect(await screen.findByText('You have a session in progress: question 2 of 2.')).toBeInTheDocument()
    await fireEvent.click(screen.getByRole('button', { name: 'Resume session' }))
    expect(await screen.findByText('Question 2 of 2')).toBeInTheDocument()
    expect(screen.getByLabelText('Session score')).toHaveTextContent('1/1 correct')
    second.unmount()

    render(Today, { day: '2026-11-16' })
    await fireEvent.click(await screen.findByRole('button', { name: 'Start over' }))
    expect(screen.getByRole('button', { name: 'Start session' })).toBeInTheDocument()
    expect(sessionStorage.getItem('holdem.today')).toBeNull()
  })

  it('forgets the saved session once it is finished', async () => {
    sessionStorage.clear()
    mocked.today.mockResolvedValue({ due: [], new: ['pot-odds'], extra: [], queue: ['pot-odds'] })
    mocked.answer.mockResolvedValue({ ...correctResult })
    const user = userEvent.setup()
    render(Today, { day: '2026-11-16' })
    await fireEvent.click(await screen.findByRole('button', { name: 'Start session' }))
    await user.type(await screen.findByLabelText('Your answer'), '25{Enter}')
    await screen.findByRole('button', { name: /Next/ })
    expect(sessionStorage.getItem('holdem.today')).toBeNull()
  })

  it('uses the current local date by default', async () => {
    sessionStorage.clear()
    render(Today)
    expect(await screen.findByRole('button', { name: 'Start session' })).toBeInTheDocument()
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
    expect(screen.getByText(/Mastery 60% over your last 3 answers/)).toBeInTheDocument()
    expect(screen.getByText('Reading the board').parentElement).toHaveTextContent('Reading the board, ghost')
    expect(screen.getByText('Tier 1 · Core maths')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Pot odds' })).toHaveAttribute('href', '#/math-lab/pot-odds')
    expect(screen.getByRole('link', { name: 'unlisted' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Reading the board' })).toHaveAttribute('href', '#/learn/board-reading')
    expect(screen.getByRole('link', { name: 'ghost' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: '2016 L1 · Overview' })).toHaveAttribute('rel', 'noreferrer')
  })

  it('handles concepts without drills or prerequisites', async () => {
    render(Learn, { selected: 'icm' })
    expect(await screen.findByText(/Coming soon/)).toBeInTheDocument()
    expect(screen.queryByText(/Mastery .* over your last/)).toBeNull()
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

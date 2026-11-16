import { fireEvent, render, screen } from '@testing-library/svelte'
import { describe, expect, it, vi } from 'vitest'
import { activity, drills } from '../../test/fixtures'
import Confetti from './Confetti.svelte'
import GoalRing from './GoalRing.svelte'
import Heatmap from './Heatmap.svelte'
import SessionSummary from './SessionSummary.svelte'

const row = (drill: string, correct: boolean, ms = 2000) => ({ drill, correct, ms })

describe('Confetti', () => {
  it('renders the requested number of hidden pieces', () => {
    const { container } = render(Confetti, { pieces: 12, random: () => 0.5 })
    expect(container.querySelectorAll('span')).toHaveLength(12)
    expect(container.querySelector('.confetti')).toHaveAttribute('aria-hidden', 'true')
  })

  it('defaults to a full burst', () => {
    const { container } = render(Confetti)
    expect(container.querySelectorAll('span')).toHaveLength(70)
  })
})

describe('SessionSummary', () => {
  const base = { drills, bestStreak: 3, onrestart: vi.fn(), nextHref: '#/learn', nextLabel: 'Learn' }

  it('celebrates a strong session and breaks it down by drill', async () => {
    const results = [
      ...Array.from({ length: 4 }, () => row('pot-odds', true)),
      row('showdown', true),
      row('mystery', false),
    ]
    const { container } = render(SessionSummary, { ...base, results })
    expect(screen.getByText('Solid work. The misses are what the next review is for.')).toBeInTheDocument()
    expect(screen.getByText('83%')).toBeInTheDocument()
    expect(screen.getByText('🔥 3')).toBeInTheDocument()
    expect(screen.getByText('2.0s')).toBeInTheDocument()
    expect(screen.getByText('mystery')).toBeInTheDocument()
    expect(screen.getByText('4/4')).toBeInTheDocument()
    expect(container.parentElement?.querySelector('.confetti')).not.toBeNull()
    await fireEvent.click(screen.getByRole('button', { name: 'Play again' }))
    expect(base.onrestart).toHaveBeenCalled()
    expect(screen.getByRole('link', { name: 'Learn' })).toHaveAttribute('href', '#/learn')
  })

  it.each([
    [[row('pot-odds', true)], 'Outstanding. That is a winning session.'],
    [[row('pot-odds', false)], 'Tough spots.'],
    [[], 'No answers this time.'],
  ])('picks a verdict for %j', (results, text) => {
    render(SessionSummary, { ...base, results, skipped: 2 })
    expect(screen.getByText(new RegExp(text.replace('.', '\\.')))).toBeInTheDocument()
    expect(screen.getByText('Skipped 2.')).toBeInTheDocument()
    expect(document.querySelector('.confetti')).toBeNull()
    expect(screen.queryByRole('list')).toBeNull()
  })
})

describe('GoalRing', () => {
  it('shows progress and turns gold when the goal is met', () => {
    const { container, unmount } = render(GoalRing, { value: 5, goal: 20, label: 'Answers today' })
    expect(screen.getByRole('figure', { name: 'Answers today: 5 of 20' })).toBeInTheDocument()
    expect(container.querySelector('.fill')).not.toHaveClass('done')
    unmount()
    const done = render(GoalRing, { value: 25, goal: 20, label: 'Goal' })
    expect(done.container.querySelector('.fill')).toHaveClass('done')
  })
})

describe('Heatmap', () => {
  it('pads to Monday and shades days by activity', () => {
    const { container } = render(Heatmap, { history: activity.history })
    expect(screen.getByRole('img', { name: 'Practised on 2 of the last 3 days' })).toBeInTheDocument()
    // 2026-11-11 is a Wednesday: two blanks for Monday and Tuesday.
    expect(container.querySelectorAll('.blank')).toHaveLength(2)
    const cells = container.querySelectorAll('.cells .cell')
    expect(cells[0]).toHaveClass('level-0')
    expect(cells[1]).toHaveAttribute('title', '2026-11-12: 3 answers, 2 correct')
    expect(cells[2]).toHaveClass('level-4')
    expect(cells[0]).toHaveAttribute('title', '2026-11-11: 0 answers')
  })

  it('handles an empty history', () => {
    const { container } = render(Heatmap, { history: [] })
    expect(container.querySelectorAll('.blank')).toHaveLength(0)
  })
})

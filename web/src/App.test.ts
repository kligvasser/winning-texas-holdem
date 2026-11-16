import { render, screen } from '@testing-library/svelte'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import App from './App.svelte'
import { router } from './lib/router.svelte'
import { drills } from './test/fixtures'

vi.mock('./lib/api', () => ({
  api: {
    drills: vi.fn(() => Promise.resolve(drills)),
    stats: vi.fn(() => Promise.resolve([])),
    today: vi.fn(() => Promise.resolve({ due: [], new: [], extra: [], queue: [] })),
    activity: vi.fn(() =>
      Promise.resolve({
        today: '2026-11-16',
        answered_today: 0,
        correct_today: 0,
        practiced_today: false,
        streak: 0,
        best_streak: 0,
        total: 0,
        history: [],
      }),
    ),
    curriculum: vi.fn(() => Promise.resolve({ concepts: [], cards: {}, materials: [] })),
    spots: vi.fn(() => Promise.resolve([])),
    leaks: vi.fn(() => Promise.resolve([])),
    question: vi.fn(() => new Promise(() => {})),
    answer: vi.fn(),
  },
}))

async function visit(hash: string) {
  router.go(...(hash.split('/').filter(Boolean) as [string, ...string[]]))
  window.dispatchEvent(new HashChangeEvent('hashchange'))
  await Promise.resolve()
}

beforeEach(() => {
  window.location.hash = ''
})

describe('App', () => {
  it('routes between pages and marks the active link', async () => {
    render(App)
    await visit('home')
    expect(screen.getByRole('heading', { name: "Winning Texas Hold'em" })).toBeInTheDocument()

    await visit('today')
    expect(await screen.findByText(/Nothing is due/)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Today' })).toHaveAttribute('aria-current', 'page')

    await visit('learn')
    expect(await screen.findByRole('heading', { name: 'Curriculum' })).toBeInTheDocument()

    await visit('math-lab')
    expect(await screen.findByRole('heading', { name: 'Math Lab' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Today' })).not.toHaveAttribute('aria-current')

    await visit('math-lab/pot-odds')
    expect(await screen.findByText('Dealing…')).toBeInTheDocument()

    await visit('preflop')
    expect(await screen.findByRole('heading', { name: 'Preflop' })).toBeInTheDocument()

    await visit('speed/mixed')
    expect(await screen.findByRole('heading', { name: 'Speed round' })).toBeInTheDocument()
    expect(document.title).toBe("Speed round · Hold'em Trainer")

    await visit('stats')
    expect(await screen.findByText(/No answers yet/)).toBeInTheDocument()

    await visit('nowhere')
    expect(screen.getByRole('heading', { name: 'Not found' })).toBeInTheDocument()
  })
})

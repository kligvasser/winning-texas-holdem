import { render, screen } from '@testing-library/svelte'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import App from './App.svelte'
import { router } from './lib/router.svelte'
import { drills } from './test/fixtures'

vi.mock('./lib/api', () => ({
  api: {
    drills: vi.fn(() => Promise.resolve(drills)),
    stats: vi.fn(() => Promise.resolve([])),
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
    expect(screen.getByRole('link', { name: 'Home' })).toHaveAttribute('aria-current', 'page')

    await visit('math-lab')
    expect(await screen.findByRole('heading', { name: 'Math Lab' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Home' })).not.toHaveAttribute('aria-current')

    await visit('math-lab/pot-odds')
    expect(await screen.findByText('Dealing…')).toBeInTheDocument()

    await visit('stats')
    expect(await screen.findByText(/No answers yet/)).toBeInTheDocument()

    await visit('nowhere')
    expect(screen.getByRole('heading', { name: 'Not found' })).toBeInTheDocument()
  })
})

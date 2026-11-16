import { fireEvent, render, screen } from '@testing-library/svelte'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { api } from '../api'
import { decisions, handView, playState } from '../../test/fixtures'
import Play from './Play.svelte'
import Review from './Review.svelte'

vi.mock('../api', () => ({
  api: {
    styles: vi.fn(),
    play: vi.fn(),
    act: vi.fn(),
    nextHand: vi.fn(),
    coach: vi.fn(),
    hands: vi.fn(),
    hand: vi.fn(),
  },
}))
const mocked = vi.mocked(api)

const finished = playState({
  hand: handView({ finished: true, current: null, net: [20, -20], hole: [['As', 'Kd'], ['Qs', 'Qd']] }),
  legal: null,
  hands_played: 1,
  net_bb: 10,
  decisions,
  hand_id: 3,
})

beforeEach(() => {
  vi.resetAllMocks()
  mocked.styles.mockResolvedValue([
    { key: 'maniac', name: 'Maniac', blurb: 'Raises constantly.' },
    { key: 'nit', name: 'Nit', blurb: 'Plays few hands.' },
  ])
  mocked.play.mockResolvedValue(playState())
  mocked.coach.mockResolvedValue({ to_call_bb: 2, pot_bb: 12, need: 0.14, equity: 0.62, range_share: 0.95 })
})

describe('Play', () => {
  it('starts against a chosen opponent and plays a hand to its review', async () => {
    render(Play)
    expect(screen.getByText('Loading…')).toBeInTheDocument()
    await fireEvent.click(await screen.findByRole('button', { name: /Maniac/ }))
    expect(mocked.play).toHaveBeenCalledWith('maniac')
    expect(await screen.findByRole('region', { name: 'Poker table' })).toBeInTheDocument()
    expect(screen.getByText('· hand 1', { exact: false })).toBeInTheDocument()

    mocked.act.mockResolvedValueOnce(finished)
    await fireEvent.click(screen.getByRole('button', { name: /Call/ }))
    expect(mocked.act).toHaveBeenCalledWith('s1', 'call', undefined)
    expect(await screen.findByRole('heading', { name: 'You win 10bb' })).toBeInTheDocument()
    expect(screen.getByLabelText('Session result')).toHaveTextContent('+10bb')
    expect(screen.getByText('Mistake')).toBeInTheDocument()
    expect(screen.queryByRole('group', { name: 'Your action' })).toBeNull()

    mocked.nextHand.mockResolvedValueOnce(playState({ hands_played: 1 }))
    await fireEvent.keyDown(window, { key: 'n' })
    expect(mocked.nextHand).toHaveBeenCalledWith('s1')
    expect(await screen.findByRole('group', { name: 'Your action' })).toBeInTheDocument()
    await fireEvent.keyDown(window, { key: 'n' }) // ignored mid-hand
    expect(mocked.nextHand).toHaveBeenCalledTimes(1)
  })

  it('shows the coach on request and keeps it updated', async () => {
    render(Play)
    await fireEvent.click(await screen.findByRole('button', { name: /Maniac/ }))
    await fireEvent.click(await screen.findByRole('checkbox', { name: 'Coach' }))
    expect(await screen.findByLabelText('Coach', { selector: 'p' })).toHaveTextContent('needs 14%')
    expect(screen.getByText('62%')).toBeInTheDocument()
    mocked.act.mockResolvedValueOnce(playState())
    mocked.coach.mockResolvedValueOnce({ to_call_bb: 0, pot_bb: 12, need: null, equity: 0.4, range_share: 0.5 })
    await fireEvent.click(screen.getByRole('button', { name: /Call/ }))
    expect(await screen.findByText('40%')).toBeInTheDocument()
    expect(screen.queryByText(/needs/)).toBeNull()
    await fireEvent.click(screen.getByRole('checkbox', { name: 'Coach' }))
    expect(screen.queryByLabelText('Coach', { selector: 'p' })).toBeNull()
  })

  it('reports losses, splits, errors and lets you change opponent', async () => {
    mocked.play.mockResolvedValueOnce(
      playState({ hand: handView({ finished: true, current: null, net: [-6, 6] }), legal: null, net_bb: -3 }),
    )
    render(Play)
    await fireEvent.click(await screen.findByRole('button', { name: /Nit/ }))
    expect(await screen.findByRole('heading', { name: 'You lose 3bb' })).toBeInTheDocument()
    expect(screen.getByLabelText('Session result')).toHaveTextContent('-3bb')
    mocked.nextHand.mockRejectedValueOnce(new Error('session not found'))
    await fireEvent.click(screen.getByRole('button', { name: /Next hand/ }))
    expect(await screen.findByRole('alert')).toHaveTextContent('session not found')
    mocked.nextHand.mockResolvedValueOnce(
      playState({ hand: handView({ finished: true, current: null, net: [0, 0] }), legal: null }),
    )
    await fireEvent.click(screen.getByRole('button', { name: /Next hand/ }))
    expect(await screen.findByRole('heading', { name: 'Split pot' })).toBeInTheDocument()
    await fireEvent.click(screen.getByRole('button', { name: 'Change opponent' }))
    expect(screen.getByRole('button', { name: /Maniac/ })).toBeInTheDocument()
  })

  it('shows load failures and a coach that fails quietly', async () => {
    mocked.styles.mockRejectedValueOnce(new Error('offline'))
    const { unmount } = render(Play)
    expect(await screen.findByRole('alert')).toHaveTextContent('offline')
    unmount()
    mocked.coach.mockRejectedValue(new Error('no'))
    render(Play)
    await fireEvent.click(await screen.findByRole('button', { name: /Maniac/ }))
    await fireEvent.click(await screen.findByRole('checkbox', { name: 'Coach' }))
    expect(screen.queryByLabelText('Coach', { selector: 'p' })).toBeNull()
  })

  it('sends one action even when you click twice quickly', async () => {
    render(Play)
    await fireEvent.click(await screen.findByRole('button', { name: /Maniac/ }))
    let release: (s: ReturnType<typeof playState>) => void = () => {}
    mocked.act.mockImplementationOnce(() => new Promise((resolve) => (release = resolve)))
    const call = await screen.findByRole('button', { name: /Call/ })
    // Both clicks land before the page re-renders the button as disabled.
    call.click()
    call.click()
    await fireEvent.keyDown(window, { key: 'c' })
    expect(mocked.act).toHaveBeenCalledTimes(1)
    release(playState())
  })

  it('lists the action log in words', async () => {
    render(Play)
    await fireEvent.click(await screen.findByRole('button', { name: /Maniac/ }))
    expect(await screen.findByText('You raise to 2.5bb')).toBeInTheDocument()
    expect(screen.getByText('Maniac posts 1bb')).toBeInTheDocument()
  })
})

describe('Review', () => {
  const summary = (id: number, over = {}) => ({
    id,
    created_at: '2026-11-16T12:00:00',
    style: 'maniac',
    net_bb: 5,
    worst_loss_bb: 0,
    hole: ['As', 'Kd'],
    board: ['Kh', '7d', '2c'],
    mistakes: 0,
    ...over,
  })

  it('lists hands worst first with stats and filters to mistakes', async () => {
    mocked.hands.mockResolvedValue({
      hands: [summary(1), summary(2, { net_bb: -8, worst_loss_bb: 4, mistakes: 2, board: [] })],
      stats: { hands: 2, net_bb: -3, bb_per_100: -150, vpip: 0.5, pfr: 0.5 },
    })
    render(Review)
    expect(screen.getByText('Loading…')).toBeInTheDocument()
    const links = await screen.findAllByRole('link', { name: /vs maniac/ })
    expect(links[0]).toHaveAttribute('href', '#/review/2')
    expect(screen.getByText('2 mistakes · −4bb')).toBeInTheDocument()
    expect(screen.getByText('no flop')).toBeInTheDocument()
    expect(screen.getByText('-3bb')).toHaveClass('lost')
    expect(screen.getByText('-150bb per 100 hands')).toBeInTheDocument()
    await fireEvent.click(screen.getByLabelText('Only hands with mistakes'))
    expect(screen.getAllByRole('link', { name: /vs maniac/ })).toHaveLength(1)
  })

  it('handles winning stats, a single mistake, and an empty filter', async () => {
    mocked.hands.mockResolvedValue({
      hands: [summary(1, { mistakes: 1, worst_loss_bb: 1.2 })],
      stats: { hands: 1, net_bb: 5, bb_per_100: 500, vpip: null, pfr: null },
    })
    const { unmount } = render(Review)
    expect(await screen.findByText('1 mistake · −1.2bb')).toBeInTheDocument()
    expect(screen.getByText('+5bb', { selector: 'strong' })).toHaveClass('won')
    unmount()
    mocked.hands.mockResolvedValue({
      hands: [summary(1)],
      stats: { hands: 1, net_bb: 0, bb_per_100: 0, vpip: 1, pfr: 0 },
    })
    render(Review)
    await screen.findAllByRole('link', { name: /vs maniac/ })
    await fireEvent.click(screen.getByLabelText('Only hands with mistakes'))
    expect(screen.getByText('No hands with mistakes. Nice.')).toBeInTheDocument()
  })

  it('invites you to play when there are no hands', async () => {
    mocked.hands.mockResolvedValue({ hands: [], stats: { hands: 0, net_bb: 0, bb_per_100: null, vpip: null, pfr: null } })
    render(Review)
    expect(await screen.findByRole('link', { name: 'Play a few hands' })).toHaveAttribute('href', '#/play')
  })

  it('shows one hand with its table, decisions and log', async () => {
    mocked.hand.mockResolvedValue({
      ...summary(7),
      record: { style: 'maniac', hand: finished.hand, net_bb: 10, decisions },
    })
    render(Review, { selected: '7' })
    expect(screen.getByText('Loading…')).toBeInTheDocument()
    expect(await screen.findByRole('heading', { name: 'Hand #7 vs maniac' })).toBeInTheDocument()
    expect(screen.getByRole('region', { name: 'Poker table' })).toBeInTheDocument()
    expect(screen.getByText('Mistake')).toBeInTheDocument()
    expect(screen.getByText('preflop: You raise to 2.5bb')).toBeInTheDocument()
    expect(mocked.hand).toHaveBeenCalledWith(7)
  })

  it('reports load failures', async () => {
    mocked.hands.mockRejectedValue(new Error('offline'))
    const { unmount } = render(Review)
    expect(await screen.findByRole('alert')).toHaveTextContent('Could not load hands: offline')
    unmount()
    mocked.hand.mockRejectedValue(new Error('hand not found'))
    render(Review, { selected: '99' })
    expect(await screen.findByRole('alert')).toHaveTextContent('hand not found')
  })
})

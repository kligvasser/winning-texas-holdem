import { fireEvent, render, screen } from '@testing-library/svelte'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { api } from '../api'
import { decisions, frame, handView, playState, seats } from '../../test/fixtures'
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

const done = (net: number[], winners: number[]) =>
  handView({ finished: true, current: null, net, winners, bets: [0, 0, 0, 0, 0, 0] })

const finished = playState({
  hand: done([20, -18, -2, 0, 0, 0], [0]),
  frames: [frame({ finished: true, current: null, net: [20, -18, -2, 0, 0, 0], winners: [0] })],
  legal: null,
  hands_played: 1,
  net_bb: 10,
  decisions,
  hand_id: 3,
})

beforeEach(() => {
  vi.resetAllMocks()
  mocked.styles.mockResolvedValue(seats.slice(1))
  mocked.play.mockResolvedValue(playState())
  mocked.coach.mockResolvedValue({ to_call_bb: 2, pot_bb: 12, need: 0.14, equity: 0.62, opponents: 1 })
})

const sit = async () => fireEvent.click(await screen.findByRole('button', { name: 'Deal me in!' }))

describe('Play', () => {
  it('introduces the table, then plays a hand to its review', async () => {
    render(Play, { pace: 0 })
    expect(screen.getByText('Loading…')).toBeInTheDocument()
    expect(await screen.findByText('Calling station')).toBeInTheDocument()
    expect(screen.getByRole('img', { name: 'Blaze' })).toBeInTheDocument()
    await sit()
    expect(mocked.play).toHaveBeenCalled()
    expect(await screen.findByRole('region', { name: 'Poker table' })).toBeInTheDocument()
    expect(screen.getByText('Hand 1')).toBeInTheDocument()

    mocked.act.mockResolvedValueOnce(finished)
    await fireEvent.click(screen.getByRole('button', { name: /Call/ }))
    expect(mocked.act).toHaveBeenCalledWith('s1', 'call', undefined)
    expect(await screen.findByRole('heading', { name: 'You win 10bb!' })).toBeInTheDocument()
    expect(screen.getByLabelText('Session result')).toHaveTextContent('+10bb')
    expect(screen.getByText('Mistake')).toBeInTheDocument()
    expect(screen.queryByRole('group', { name: 'Your action' })).toBeNull()
    expect(document.querySelector('.confetti')).toBeInTheDocument()
    expect(document.querySelector('.winflash')).toBeInTheDocument()

    mocked.nextHand.mockResolvedValueOnce(playState({ hands_played: 1 }))
    await fireEvent.keyDown(window, { key: 'n' })
    expect(mocked.nextHand).toHaveBeenCalledWith('s1')
    expect(await screen.findByRole('group', { name: 'Your action' })).toBeInTheDocument()
    await fireEvent.keyDown(window, { key: 'n' }) // ignored mid-hand
    await fireEvent.keyDown(window, { key: ' ' }) // nothing to skip
    expect(mocked.nextHand).toHaveBeenCalledTimes(1)
  })

  it('shows the coach on request and keeps it updated', async () => {
    render(Play, { pace: 0 })
    await sit()
    await fireEvent.click(await screen.findByRole('checkbox', { name: 'Coach' }))
    const coach = await screen.findByLabelText('Coach', { selector: 'p' })
    expect(coach).toHaveTextContent('needs 14%')
    expect(coach).toHaveTextContent("the bot's likely range: 62%")
    mocked.act.mockResolvedValueOnce(playState())
    mocked.coach.mockResolvedValueOnce({ to_call_bb: 0, pot_bb: 12, need: null, equity: 0.4, opponents: 3 })
    await fireEvent.click(screen.getByRole('button', { name: /Call/ }))
    expect(await screen.findByText('40%')).toBeInTheDocument()
    expect(screen.getByLabelText('Coach', { selector: 'p' })).toHaveTextContent("3 bots' likely ranges")
    expect(screen.queryByText(/needs/)).toBeNull()
    await fireEvent.click(screen.getByRole('checkbox', { name: 'Coach' }))
    expect(screen.queryByLabelText('Coach', { selector: 'p' })).toBeNull()
  })

  it('reports losses, pots you were not in, errors and lets you leave', async () => {
    mocked.play.mockResolvedValueOnce(
      playState({ hand: done([-6, 6, 0, 0, 0, 0], [1]), legal: null, net_bb: -3 }),
    )
    render(Play, { pace: 0 })
    await sit()
    expect(await screen.findByRole('heading', { name: 'You lose 3bb' })).toBeInTheDocument()
    expect(screen.getByLabelText('Session result')).toHaveTextContent('-3bb')
    expect(document.querySelector('.confetti')).toBeNull()
    mocked.nextHand.mockRejectedValueOnce(new Error('session not found'))
    await fireEvent.click(screen.getByRole('button', { name: /Next hand/ }))
    expect(await screen.findByRole('alert')).toHaveTextContent('session not found')
    mocked.nextHand.mockResolvedValueOnce(playState({ hand: done([0, 3, -3, 0, 0, 0], [1]), legal: null }))
    await fireEvent.click(screen.getByRole('button', { name: /Next hand/ }))
    expect(await screen.findByRole('heading', { name: 'Rocky takes the pot' })).toBeInTheDocument()
    mocked.nextHand.mockResolvedValueOnce(playState({ hand: done([0, 1, 1, -2, 0, 0], [1, 2]), legal: null }))
    await fireEvent.click(screen.getByRole('button', { name: /Next hand/ }))
    expect(await screen.findByRole('heading', { name: 'Rocky & Finn split the pot' })).toBeInTheDocument()
    await fireEvent.click(screen.getByRole('button', { name: 'Leave table' }))
    expect(screen.getByRole('button', { name: 'Deal me in!' })).toBeInTheDocument()
  })

  it('shows load failures and a coach that fails quietly', async () => {
    mocked.styles.mockRejectedValueOnce(new Error('offline'))
    const { unmount } = render(Play, { pace: 0 })
    expect(await screen.findByRole('alert')).toHaveTextContent('offline')
    unmount()
    mocked.coach.mockRejectedValue(new Error('no'))
    render(Play, { pace: 0 })
    await sit()
    await fireEvent.click(await screen.findByRole('checkbox', { name: 'Coach' }))
    expect(screen.queryByLabelText('Coach', { selector: 'p' })).toBeNull()
  })

  it('sends one action even when you click twice quickly', async () => {
    render(Play, { pace: 0 })
    await sit()
    let release: (s: ReturnType<typeof playState>) => void = () => {}
    mocked.act.mockImplementationOnce(() => new Promise((resolve) => (release = resolve)))
    const call = await screen.findByRole('button', { name: /Call/ })
    // Both clicks land before the page re-renders the button as disabled.
    call.click()
    call.click()
    await fireEvent.keyDown(window, { key: 'c' })
    await fireEvent.keyDown(window, { key: 'n' })
    expect(mocked.act).toHaveBeenCalledTimes(1)
    release(playState())
  })

  it('lists the action log in words', async () => {
    render(Play, { pace: 0 })
    await sit()
    expect(await screen.findByText('You raise to 2.5bb')).toBeInTheDocument()
    expect(screen.getByText('Rocky posts 0.5bb')).toBeInTheDocument()
  })

  describe('step by step', () => {
    const call = frame({
      street: 'preflop',
      board: [],
      bets: [5, 5, 2, 0, 0, 0],
      pot: 12,
      current: 2,
      last: { street: 'preflop', player: 1, kind: 'call', amount: 4, to: 5, pot: 8, to_call: 4 },
    })
    const fold = frame({
      street: 'preflop',
      board: [],
      bets: [5, 5, 2, 0, 0, 0],
      pot: 12,
      current: 1,
      last: { street: 'preflop', player: 2, kind: 'fold', amount: 0, to: 2, pot: 12, to_call: 3 },
    })
    const steps = () => playState({ frames: [call, fold, frame({ bets: [0, 0, 0, 0, 0, 0] })] })

    beforeEach(() => {
      vi.useFakeTimers()
      mocked.play.mockResolvedValue(steps())
    })
    afterEach(() => vi.useRealTimers())

    it('plays the bots one action at a time, sweeping bets into the pot', async () => {
      render(Play, { pace: 100 })
      await vi.advanceTimersByTimeAsync(0)
      await fireEvent.click(screen.getByRole('button', { name: 'Deal me in!' }))
      await vi.advanceTimersByTimeAsync(0)
      expect(screen.getByText('Call 2bb')).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /Skip/ })).toBeInTheDocument()
      expect(screen.queryByRole('group', { name: 'Your action' })).toBeNull()
      await fireEvent.keyDown(window, { key: 'n' }) // not over yet
      await vi.advanceTimersByTimeAsync(100)
      expect(screen.getByText('Fold')).toBeInTheDocument()
      expect(document.querySelectorAll('.fly.in')).toHaveLength(0)
      await vi.advanceTimersByTimeAsync(50)
      expect(screen.getByText('Bet 2bb')).toBeInTheDocument()
      expect(document.querySelectorAll('.fly.in')).toHaveLength(3)
      expect(screen.getByRole('group', { name: 'Your action' })).toBeInTheDocument()
      await vi.advanceTimersByTimeAsync(500)
      expect(screen.getByText('Bet 2bb')).toBeInTheDocument()
    })

    it('skips to your turn with the button or the space bar, and stops when you leave', async () => {
      render(Play, { pace: 100 })
      await vi.advanceTimersByTimeAsync(0)
      await fireEvent.click(screen.getByRole('button', { name: 'Deal me in!' }))
      await vi.advanceTimersByTimeAsync(0)
      await fireEvent.click(screen.getByRole('button', { name: /Skip/ }))
      expect(screen.getByRole('group', { name: 'Your action' })).toBeInTheDocument()
      mocked.act.mockResolvedValueOnce(steps())
      await fireEvent.click(screen.getByRole('button', { name: /Call/ }))
      await vi.advanceTimersByTimeAsync(0)
      await fireEvent.keyDown(window, { key: ' ' })
      expect(screen.getByRole('group', { name: 'Your action' })).toBeInTheDocument()
      mocked.act.mockResolvedValueOnce(steps())
      await fireEvent.click(screen.getByRole('button', { name: /Call/ }))
      await vi.advanceTimersByTimeAsync(0)
      await fireEvent.click(screen.getByRole('button', { name: 'Leave table' }))
      await vi.advanceTimersByTimeAsync(500)
      expect(screen.getByRole('button', { name: 'Deal me in!' })).toBeInTheDocument()
    })
  })
})

describe('Review', () => {
  const summary = (id: number, over = {}) => ({
    id,
    created_at: '2026-11-16T12:00:00',
    style: '6-max',
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
    const links = await screen.findAllByRole('link', { name: /6-max/ })
    expect(links[0]).toHaveAttribute('href', '#/review/2')
    expect(screen.getByText('2 mistakes · −4bb')).toBeInTheDocument()
    expect(screen.getByText('no flop')).toBeInTheDocument()
    expect(screen.getByText('-3bb')).toHaveClass('lost')
    expect(screen.getByText('-150bb per 100 hands')).toBeInTheDocument()
    await fireEvent.click(screen.getByLabelText('Only hands with mistakes'))
    expect(screen.getAllByRole('link', { name: /6-max/ })).toHaveLength(1)
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
    await screen.findAllByRole('link', { name: /6-max/ })
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
      record: { style: '6-max', seats, hand: finished.hand, net_bb: 10, decisions },
    })
    render(Review, { selected: '7' })
    expect(screen.getByText('Loading…')).toBeInTheDocument()
    expect(await screen.findByRole('heading', { name: 'Hand #7' })).toBeInTheDocument()
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

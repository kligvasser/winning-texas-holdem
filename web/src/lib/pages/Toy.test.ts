import { fireEvent, render, screen } from '@testing-library/svelte'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { api, type ToyResult, type ToyState } from '../api'
import Toy from './Toy.svelte'

vi.mock('../api', () => ({ api: { toyMenu: vi.fn(), toyStart: vi.fn(), toyAct: vi.fn() } }))
const mocked = vi.mocked(api)

const games = [
  { key: 'akq', name: 'The AKQ game', blurb: 'Three cards.', cards: ['Q', 'K', 'A'] },
  { key: 'ten', name: 'The 1 to 10 game', blurb: 'Ten cards.', cards: ['1', '2', '3'] },
]
const opponents = [
  { key: 'tag', character: 'Finn', name: 'Optimal', blurb: 'Copy it.' },
  { key: 'nit', character: 'Rocky', name: 'Nit', blurb: 'Bluff it every time.' },
]
const frequency = { n: 0, yours: null, optimal: 0.333, best: 1 }

const toy = (over: Partial<ToyState> = {}): ToyState => ({
  id: 't1',
  game: games[0],
  opponent: opponents[1],
  hand: { number: 1, role: 'bettor', card: 'Q', actions: ['bet', 'check'], before: [] },
  last: null,
  hands_played: 0,
  summary: {
    chips: 0,
    expected: 0,
    best: 0,
    cards: games[0].cards.map((card) => ({ card, bet: frequency, call: frequency })),
  },
  ...over,
})

const result = (over: Partial<ToyResult> = {}): ToyResult => ({
  role: 'bettor',
  card: 'Q',
  their_card: 'K',
  their_action: 'fold',
  chips: 1,
  action: 'bet',
  values: { bet: 1, check: -1 },
  best: 'bet',
  active: 'bet',
  optimal: 0.333,
  lesson: 'Right: against Rocky, to bet the Q earns +1.00 chips.',
  ...over,
})

const afterBet = toy({
  hand: {
    number: 3,
    role: 'caller',
    card: 'K',
    actions: ['call', 'fold'],
    before: [{ role: 'caller', card: 'A', their_card: 'K', their_action: 'check', chips: 1 }],
  },
  last: result(),
  hands_played: 2,
  summary: {
    chips: 2,
    expected: 1.5,
    best: 2,
    cards: games[0].cards.map((card) => ({
      card,
      bet: card === 'Q' ? { n: 1, yours: 1, optimal: 0.333, best: 1 } : frequency,
      call: frequency,
    })),
  },
})

beforeEach(() => {
  vi.resetAllMocks()
  mocked.toyMenu.mockResolvedValue({ games, opponents })
  mocked.toyStart.mockResolvedValue(toy())
})

const sit = async () => fireEvent.click(await screen.findByRole('button', { name: 'Play Rocky' }))

describe('Toy', () => {
  it('picks a game and an opponent, then plays a hand', async () => {
    render(Toy)
    expect(screen.getByText('Loading…')).toBeInTheDocument()
    const ten = await screen.findByRole('button', { name: /The 1 to 10 game/ })
    expect(screen.getByRole('button', { name: /The AKQ game/ })).toHaveAttribute('aria-pressed', 'true')
    await fireEvent.click(ten)
    expect(ten).toHaveAttribute('aria-pressed', 'true')
    await fireEvent.keyDown(window, { key: 'b' }) // no game yet: nothing happens
    await sit()
    expect(mocked.toyStart).toHaveBeenCalledWith('ten', 'nit')

    expect(await screen.findByRole('region', { name: 'Toy table' })).toBeInTheDocument()
    expect(screen.getByText('Hand 1')).toBeInTheDocument()
    expect(screen.getByLabelText('Your card: Q')).toBeInTheDocument()
    expect(screen.getByLabelText("Rocky's card is hidden")).toBeInTheDocument()
    expect(screen.getByText(/You act: bet 1 chip or check/)).toBeInTheDocument()
    expect(screen.getByLabelText('Session result')).toHaveTextContent('0 chips')
    expect(screen.getByRole('row', { name: /^Q – 33% 100%/ })).toBeInTheDocument()

    mocked.toyAct.mockResolvedValueOnce(afterBet)
    await fireEvent.click(screen.getByRole('button', { name: /Bet 1/ }))
    expect(mocked.toyAct).toHaveBeenCalledWith('t1', 'bet')
    expect(await screen.findByRole('heading', { name: 'You win 1 chip!' })).toBeInTheDocument()
    expect(screen.getByLabelText("Rocky's card: K")).toBeInTheDocument()
    expect(screen.getByText('You bet. Rocky folded with the K.')).toBeInTheDocument()
    expect(screen.getByText(/Right: against Rocky/)).toBeInTheDocument()
    expect(screen.getByText('+1 chips on average').closest('li')).toHaveClass('best', 'yours')
    expect(screen.getByText('your play')).toBeInTheDocument()
    expect(screen.getByText('Hand 1')).toBeInTheDocument()
    expect(screen.getByLabelText('Session result')).toHaveClass('up')
    expect(screen.getByRole('row', { name: /^Q 100% of 1/ })).toBeInTheDocument()
    expect(screen.getByRole('img', { name: 'You' })).toHaveClass('happy')
    await fireEvent.keyDown(window, { key: 'b' }) // no betting while the result is up
    expect(mocked.toyAct).toHaveBeenCalledTimes(1)

    await fireEvent.keyDown(window, { key: 'n' })
    expect(screen.getByText('Rocky bets 1 chip into 2. Call or fold?')).toBeInTheDocument()
    expect(screen.getByText('Hand 2: you held the A. Rocky checked with the K. You won 1 chip.')).toBeInTheDocument()
    expect(screen.getByText('Hand 3')).toBeInTheDocument()

    mocked.toyAct.mockResolvedValueOnce(
      toy({
        last: result({
          role: 'caller',
          card: 'K',
          their_card: 'A',
          their_action: 'bet',
          action: 'call',
          chips: -2,
          values: { call: -2, fold: -1 },
          best: 'fold',
          active: 'call',
        }),
        hands_played: 3,
        summary: { ...afterBet.summary, chips: -1 },
      }),
    )
    await fireEvent.keyDown(window, { key: 'x' })
    await fireEvent.keyDown(window, { key: 'c', metaKey: true })
    expect(mocked.toyAct).toHaveBeenCalledTimes(1)
    await fireEvent.keyDown(window, { key: 'C' })
    expect(mocked.toyAct).toHaveBeenLastCalledWith('t1', 'call')
    expect(await screen.findByRole('heading', { name: 'You lose 2 chips' })).toBeInTheDocument()
    expect(screen.getByText('Rocky bet with the A. You called.')).toBeInTheDocument()
    expect(screen.getByLabelText('Session result')).toHaveClass('down')
    expect(screen.getByRole('img', { name: 'Rocky' })).toHaveClass('happy')

    await fireEvent.click(screen.getByRole('button', { name: /Next hand/ }))
    expect(screen.queryByRole('region', { name: 'Hand result' })).toBeNull()
    await fireEvent.click(screen.getByRole('button', { name: 'Change game' }))
    expect(screen.getByRole('heading', { name: 'Toy games' })).toBeInTheDocument()
  })

  it('shows a checked hand and moves on with Enter', async () => {
    render(Toy)
    await sit()
    mocked.toyAct.mockResolvedValueOnce(
      toy({
        last: result({ action: 'check', their_action: 'check', chips: -1, best: 'bet' }),
        hands_played: 1,
        hand: { number: 2, role: 'bettor', card: 'A', actions: ['bet', 'check'], before: [] },
      }),
    )
    await fireEvent.click(await screen.findByRole('button', { name: /Check/ }))
    expect(await screen.findByText('You checked. Rocky shows the K.')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'You lose 1 chip' })).toBeInTheDocument()
    // Enter on a focused button belongs to that button, not to "next hand".
    await fireEvent.keyDown(screen.getByRole('button', { name: 'Change game' }), { key: 'Enter' })
    expect(screen.getByRole('heading', { name: 'You lose 1 chip' })).toBeInTheDocument()
    await fireEvent.keyDown(window, { key: 'Enter' })
    expect(screen.getByLabelText('Your card: A')).toBeInTheDocument()
  })

  it('goes back to the lobby when the server has forgotten the game', async () => {
    render(Toy)
    await sit()
    mocked.toyAct.mockRejectedValueOnce(Object.assign(new Error('session not found'), { status: 404 }))
    await fireEvent.click(await screen.findByRole('button', { name: /Bet 1/ }))
    expect(await screen.findByRole('alert')).toHaveTextContent('That game is gone. Start a new one.')
    expect(screen.getByRole('button', { name: /The AKQ game/ })).toBeInTheDocument()
  })

  it('reports errors from the menu and from a move', async () => {
    mocked.toyMenu.mockRejectedValueOnce(new Error('offline'))
    const { unmount } = render(Toy)
    expect(await screen.findByRole('alert')).toHaveTextContent('offline')
    expect(screen.queryByText('Loading…')).toBeNull()
    unmount()

    render(Toy)
    await sit()
    mocked.toyAct.mockRejectedValueOnce(new Error('session not found'))
    await fireEvent.click(await screen.findByRole('button', { name: /Bet 1/ }))
    expect(await screen.findByRole('alert')).toHaveTextContent('session not found')
    expect(screen.getByRole('button', { name: /Bet 1/ })).toBeEnabled()
  })
})

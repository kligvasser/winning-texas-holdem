import { fireEvent, render, screen } from '@testing-library/svelte'
import { describe, expect, it, vi } from 'vitest'
import { decisions, handView, legal, seats } from '../../test/fixtures'
import ActionBar from './ActionBar.svelte'
import ChipStack from './ChipStack.svelte'
import DecisionList from './DecisionList.svelte'
import PokerTable from './PokerTable.svelte'

describe('PokerTable', () => {
  it('seats six players with chips, the board and hidden cards', () => {
    render(PokerTable, { hand: handView(), seats })
    expect(screen.getByRole('group', { name: 'Rocky' })).toBeInTheDocument()
    expect(screen.getByRole('group', { name: 'Finn (folded)' })).toBeInTheDocument()
    expect(screen.getByRole('group', { name: 'You' })).toHaveAttribute('aria-current', 'true')
    expect(screen.getAllByLabelText('Hidden card')).toHaveLength(2) // only Rocky is still in
    expect(screen.getByLabelText('Pot')).toHaveTextContent('Pot 8bb')
    expect(screen.getByLabelText('Chips in the pot')).toBeInTheDocument()
    expect(screen.getByLabelText('Rocky bet')).toHaveTextContent('2bb')
    expect(screen.queryByLabelText('You bet')).toBeNull()
    expect(screen.getByTitle('Dealer button')).toBeInTheDocument()
    expect(screen.getByText('Bet 2bb')).toHaveClass('k-bet')
    expect(screen.getByText('One Pair')).toBeInTheDocument()
    expect(screen.getByText('SB')).toBeInTheDocument()
    expect(screen.getByRole('img', { name: 'King of hearts' })).toBeInTheDocument()
    expect(document.querySelectorAll('.slot')).toHaveLength(2)
    expect(document.querySelectorAll('.fly')).toHaveLength(0)
    for (const kind of ['hero', 'nit', 'tag', 'lag', 'station', 'maniac']) {
      expect(document.querySelector(`[data-kind="${kind}"]`)).toBeInTheDocument()
    }
  })

  it('reveals cards, winners and results at the end', () => {
    render(PokerTable, {
      hand: handView({
        hole: [['As', 'Kd'], ['Qs', 'Qd'], null, null, null, null],
        made: ['One Pair', 'One Pair', null, null, null, null],
        finished: true,
        showdown: true,
        net: [20, -18, -2, 0, 0, 0],
        winners: [0],
        current: null,
        bets: [0, 0, 0, 0, 0, 0],
      }),
      seats,
    })
    expect(screen.getByText('+10bb')).toHaveClass('won')
    expect(screen.getByText('-9bb')).toHaveClass('lost')
    expect(screen.queryByLabelText('Hidden card')).toBeNull()
    expect(screen.getByRole('group', { name: 'You' })).toHaveClass('winner')
    expect(screen.getByRole('img', { name: 'You' })).toHaveClass('happy')
    expect(screen.getByRole('img', { name: 'Nit' })).toHaveClass('idle')
    expect(screen.getByRole('img', { name: 'TAG' })).toHaveClass('out')
    expect(document.querySelectorAll('.fly.out')).toHaveLength(1)
    expect(screen.queryByText(/^Bet/)).toBeNull() // nobody is talking once the hand is over
    expect(screen.queryByLabelText('Chips in the pot')).toBeNull()
  })

  it('flashes an all-in and sweeps the bets into the pot', () => {
    render(PokerTable, {
      hand: handView({
        behind: [195, 0, 198, 200, 200, 200],
        bets: [0, 195, 0, 0, 0, 0],
        hole: [['As', 'Kd'], null, ['Qs', 'Qd'], null, null, null],
        folded: [true, false, true, true, true, true],
        last: { street: 'flop', player: 1, kind: 'bet', amount: 195, to: 195, pot: 12, to_call: 0 },
      }),
      seats,
      sweep: [5, 5, 0, 0, 0, 0],
      tick: 3,
    })
    expect(screen.getByRole('status')).toHaveTextContent('ALL IN!')
    expect(screen.getByText('All-in 97.5bb')).toHaveClass('allin')
    expect(document.querySelectorAll('.fly.in')).toHaveLength(2)
    // You folded: your own cards stay face up, a folded bot's would not.
    expect(screen.getByRole('img', { name: 'Ace of spades' })).toBeInTheDocument()
    expect(screen.queryByRole('img', { name: 'Queen of spades' })).toBeNull()
  })
})

describe('ChipStack', () => {
  it('stacks chips in columns of five', () => {
    render(ChipStack, { chips: 99, label: 'Bet' })
    expect(screen.getByLabelText('Bet')).toHaveTextContent('49.5bb')
    expect(document.querySelectorAll('.column')).toHaveLength(2)
    expect(document.querySelectorAll('.chip')).toHaveLength(10)
  })
})

describe('ActionBar', () => {
  it('folds, calls and raises with buttons, keys and a custom size', async () => {
    const onact = vi.fn()
    render(ActionBar, { legal, pot: 24, currentBet: 0, onact })
    await fireEvent.click(screen.getByRole('button', { name: /Fold/ }))
    expect(onact).toHaveBeenLastCalledWith('fold')
    await fireEvent.click(screen.getByRole('button', { name: /Call 2bb/ }))
    expect(onact).toHaveBeenLastCalledWith('call')
    await fireEvent.click(screen.getByRole('button', { name: /Raise all-in/ }))
    expect(onact).toHaveBeenLastCalledWith('raise', 190)
    await fireEvent.click(screen.getByRole('button', { name: /^Raise 4bb/ }))
    expect(onact).toHaveBeenLastCalledWith('raise', 8)
    for (const key of ['f', 'c', '1']) await fireEvent.keyDown(window, { key })
    expect(onact.mock.calls.slice(-3)).toEqual([['fold'], ['call'], ['raise', 8]])
    const field = screen.getByLabelText('Raise to (bb)')
    await fireEvent.input(field, { target: { value: '20' } })
    await fireEvent.submit(field.closest('form')!)
    expect(onact).toHaveBeenLastCalledWith('raise', 40)
    await fireEvent.input(field, { target: { value: '12,5bb' } }) // a comma and a unit are fine
    await fireEvent.submit(field.closest('form')!)
    expect(onact).toHaveBeenLastCalledWith('raise', 25)
    const calls = onact.mock.calls.length
    await fireEvent.input(field, { target: { value: '1' } }) // below the minimum
    await fireEvent.submit(field.closest('form')!)
    expect(field).toHaveAttribute('aria-invalid', 'true')
    expect(screen.getByRole('alert')).toHaveTextContent('Enter 4 to 95bb')
    await fireEvent.input(field, { target: { value: '' } })
    expect(screen.queryByRole('alert')).toBeNull()
    await fireEvent.submit(field.closest('form')!) // nothing typed
    await fireEvent.keyDown(window, { key: 'c', repeat: true }) // a held key
    await fireEvent.keyDown(field, { key: 'f' }) // typing in the box is not a shortcut
    await fireEvent.keyDown(window, { key: 'c', metaKey: true })
    await fireEvent.keyDown(window, { key: '9' })
    expect(onact).toHaveBeenCalledTimes(calls)
  })

  it('offers check and bet when nothing is owed, and nothing when disabled', async () => {
    const onact = vi.fn()
    const free = { ...legal, to_call: 0, can_check: true, min_raise_to: 2 }
    const { unmount } = render(ActionBar, { legal: free, pot: 12, currentBet: 0, onact })
    expect(screen.queryByRole('button', { name: /Fold/ })).toBeNull()
    await fireEvent.click(screen.getByRole('button', { name: /Check/ }))
    expect(onact).toHaveBeenLastCalledWith('check')
    await fireEvent.keyDown(window, { key: 'f' })
    await fireEvent.keyDown(window, { key: 'c' })
    expect(onact).toHaveBeenLastCalledWith('check')
    await fireEvent.click(screen.getByRole('button', { name: /^Bet 3bb/ }))
    expect(onact).toHaveBeenLastCalledWith('bet', 6)
    await fireEvent.keyDown(window, { key: '1' })
    expect(onact).toHaveBeenLastCalledWith('bet', 2)
    const field = screen.getByLabelText('Bet to (bb)')
    await fireEvent.input(field, { target: { value: '5' } })
    await fireEvent.submit(field.closest('form')!)
    expect(onact).toHaveBeenLastCalledWith('bet', 10)
    unmount()
    onact.mockClear()
    render(ActionBar, { legal: { ...legal, can_raise: false }, pot: 12, currentBet: 0, disabled: true, onact })
    expect(screen.queryByLabelText(/to \(bb\)/)).toBeNull()
    await fireEvent.keyDown(window, { key: 'c' })
    expect(onact).not.toHaveBeenCalled()
  })
})

describe('DecisionList', () => {
  it('labels each decision with its verdict and cost', () => {
    render(DecisionList, { decisions })
    expect(screen.getByText('Mistake')).toBeInTheDocument()
    expect(screen.getByText('Small leak')).toBeInTheDocument()
    expect(screen.getByText('Not graded')).toBeInTheDocument()
    expect(screen.getByText('Good')).toBeInTheDocument()
    expect(screen.getByText('−7.8bb')).toBeInTheDocument()
    expect(screen.getByText('preflop: you raise 2.5bb')).toBeInTheDocument()
    expect(screen.getByText('flop: you fold')).toBeInTheDocument()
  })

  it('says when there was nothing to decide', () => {
    render(DecisionList, { decisions: [] })
    expect(screen.getByText(/no decisions/)).toBeInTheDocument()
  })
})

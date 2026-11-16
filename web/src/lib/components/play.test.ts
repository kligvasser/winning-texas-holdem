import { fireEvent, render, screen } from '@testing-library/svelte'
import { describe, expect, it, vi } from 'vitest'
import { decisions, handView, legal } from '../../test/fixtures'
import ActionBar from './ActionBar.svelte'
import DecisionList from './DecisionList.svelte'
import PokerTable from './PokerTable.svelte'

const names: [string, string] = ['You', 'Maniac']

describe('PokerTable', () => {
  it('shows seats, the board, bets and hides the bot cards', () => {
    render(PokerTable, { hand: handView(), names })
    expect(screen.getByText('Maniac')).toBeInTheDocument()
    expect(screen.getAllByLabelText('Hidden card')).toHaveLength(2)
    expect(screen.getByLabelText('Pot')).toHaveTextContent('Pot 12bb')
    expect(screen.getByLabelText('Maniac bet')).toHaveTextContent('2bb')
    expect(screen.queryByLabelText('You bet')).toBeNull()
    expect(screen.getByTitle(/Dealer button/)).toBeInTheDocument()
    expect(screen.getByRole('img', { name: 'King of hearts' })).toBeInTheDocument()
    expect(document.querySelectorAll('.slot')).toHaveLength(2)
  })

  it('reveals cards and results at the end', () => {
    render(PokerTable, {
      hand: handView({ hole: [['As', 'Kd'], ['Qs', 'Qd']], finished: true, net: [20, -20], current: null }),
      names,
    })
    expect(screen.getByText('+10bb')).toHaveClass('won')
    expect(screen.getByText('-10bb')).toHaveClass('lost')
    expect(screen.queryByLabelText('Hidden card')).toBeNull()
  })

  it('shows an even result without colour', () => {
    render(PokerTable, { hand: handView({ finished: true, net: [0, 0] }), names })
    expect(screen.getAllByText('0bb')[0]).not.toHaveClass('won')
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
    const calls = onact.mock.calls.length
    await fireEvent.input(field, { target: { value: '1' } }) // below the minimum
    await fireEvent.submit(field.closest('form')!)
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

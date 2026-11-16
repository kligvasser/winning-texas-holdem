import { fireEvent, render, screen } from '@testing-library/svelte'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { choiceQuestion, correctResult, numberQuestion, wrongResult } from '../../test/fixtures'
import AnswerInput from './AnswerInput.svelte'
import CardRow from './CardRow.svelte'
import Feedback from './Feedback.svelte'
import PlayingCard from './PlayingCard.svelte'
import QuestionView from './QuestionView.svelte'

describe('PlayingCard', () => {
  it('renders an accessible four-colour card', () => {
    render(PlayingCard, { code: 'Td', highlight: true })
    const card = screen.getByRole('img', { name: 'Ten of diamonds' })
    expect(card).toHaveClass('suit-d', 'highlight')
    expect(card).toHaveTextContent('10')
  })
})

describe('CardRow', () => {
  it('labels cards and highlights the right ones', () => {
    render(CardRow, { label: 'Board', cards: ['As', 'Kd'], highlight: ['Kd'] })
    expect(screen.getByText('Board')).toBeInTheDocument()
    expect(screen.getByRole('img', { name: 'King of diamonds' })).toHaveClass('highlight')
    expect(screen.getByRole('img', { name: 'Ace of spades' })).not.toHaveClass('highlight')
  })

  it('defaults to no highlight', () => {
    render(CardRow, { label: 'You', cards: ['As'] })
    expect(screen.getByRole('img')).not.toHaveClass('highlight')
  })
})

describe('QuestionView', () => {
  it('shows pot, bet and every hand', () => {
    render(QuestionView, { question: numberQuestion })
    expect(screen.getByText('What equity do you need?')).toBeInTheDocument()
    expect(screen.getByText('100')).toBeInTheDocument()
    expect(screen.getByText('50')).toBeInTheDocument()
    for (const label of ['Board', 'You', 'Villain']) expect(screen.getByText(label)).toBeInTheDocument()
  })

  it('shows players for showdown questions', () => {
    render(QuestionView, { question: choiceQuestion })
    expect(screen.getByText('Player 2')).toBeInTheDocument()
    expect(screen.queryByText('Pot')).toBeNull()
    expect(screen.queryByText('You')).toBeNull()
  })

  it('handles a pot without a bet and an empty payload', () => {
    const { unmount } = render(QuestionView, { question: { ...numberQuestion, payload: { pot: 10 } } })
    expect(screen.queryByText('Bet')).toBeNull()
    unmount()
    render(QuestionView, { question: { ...numberQuestion, payload: {} } })
    expect(screen.queryByRole('img')).toBeNull()
  })
})

describe('AnswerInput', () => {
  it('submits numbers with Enter and ignores empty or invalid input', async () => {
    const onsubmit = vi.fn()
    const user = userEvent.setup()
    render(AnswerInput, { question: numberQuestion, onsubmit })
    const input = screen.getByLabelText('Your answer')
    expect(input).toHaveFocus()
    expect(screen.getByText('%')).toBeInTheDocument()
    await fireEvent.submit(input.closest('form')!)
    await user.type(input, 'abc{Enter}')
    expect(onsubmit).not.toHaveBeenCalled()
    await user.clear(input)
    await user.type(input, '25.5{Enter}')
    expect(onsubmit).toHaveBeenCalledWith(25.5)
  })

  it('does not submit while disabled or react to digit keys', async () => {
    const onsubmit = vi.fn()
    render(AnswerInput, { question: { ...numberQuestion, unit: '' }, disabled: true, onsubmit })
    expect(screen.queryByText('%')).toBeNull()
    const input = screen.getByLabelText('Your answer')
    await fireEvent.input(input, { target: { value: '3' } })
    await fireEvent.submit(input.closest('form')!)
    await fireEvent.keyDown(window, { key: '1' })
    expect(onsubmit).not.toHaveBeenCalled()
  })

  it('ignores digit keys for number questions', async () => {
    const onsubmit = vi.fn()
    render(AnswerInput, { question: numberQuestion, onsubmit })
    await fireEvent.keyDown(window, { key: '1' })
    expect(onsubmit).not.toHaveBeenCalled()
  })

  it('picks choices by click or number key', async () => {
    const onsubmit = vi.fn()
    render(AnswerInput, { question: choiceQuestion, onsubmit })
    await fireEvent.click(screen.getByRole('button', { name: /Player 2/ }))
    expect(onsubmit).toHaveBeenLastCalledWith('Player 2')
    await fireEvent.keyDown(window, { key: '3' })
    expect(onsubmit).toHaveBeenLastCalledWith('Split pot')
    for (const key of ['0', '4', 'x', 'Enter']) await fireEvent.keyDown(window, { key })
    expect(onsubmit).toHaveBeenCalledTimes(2)
  })

  it('ignores keys while a choice question is disabled', async () => {
    const onsubmit = vi.fn()
    render(AnswerInput, { question: choiceQuestion, disabled: true, onsubmit })
    await fireEvent.keyDown(window, { key: '1' })
    expect(onsubmit).not.toHaveBeenCalled()
  })
})

describe('Feedback', () => {
  it('shows a correct answer and moves on', async () => {
    const onnext = vi.fn()
    render(Feedback, { result: correctResult, unit: '%', onnext })
    expect(screen.getByRole('heading')).toHaveTextContent('Correct')
    expect(screen.getByText(/bet \/ \(pot/)).toBeInTheDocument()
    expect(screen.queryByText(/pts/)).toBeNull()
    expect(screen.getByText('Key cards')).toBeInTheDocument()
    expect(screen.getByRole('img', { name: 'Ace of spades' })).toBeInTheDocument()
    const next = screen.getByRole('button', { name: /Next/ })
    expect(next).toHaveFocus()
    await fireEvent.click(next)
    expect(onnext).toHaveBeenCalled()
  })

  it('shows the error for a wrong numeric answer', () => {
    render(Feedback, { result: wrongResult, unit: '%', onnext: vi.fn() })
    expect(screen.getByRole('heading')).toHaveTextContent('Not quite')
    expect(screen.getByText('(+5 pts)')).toBeInTheDocument()
    expect(screen.queryByText('Key cards')).toBeNull()
  })

  it('handles choice answers and non-percent units', () => {
    render(Feedback, { result: { ...wrongResult, error: null, expected: 'Fold', response: 'Call' }, onnext: vi.fn() })
    expect(screen.getByText('Fold')).toBeInTheDocument()
    expect(screen.queryByText(/\(/)).toBeNull()
  })

  it('tells you when the drill comes back', () => {
    const due = new Date(Date.now() + 3 * 86_400_000).toISOString()
    render(Feedback, { result: { ...correctResult, review: { rating: 'good', due } }, onnext: vi.fn() })
    expect(screen.getByText(/Review recorded \(good\)\. This drill comes back in 3 days\./)).toBeInTheDocument()
  })

  it('shows unitless numeric errors', () => {
    render(Feedback, { result: { ...wrongResult, error: -2 }, unit: 'outs', onnext: vi.fn() })
    expect(screen.getByText('(-2)')).toBeInTheDocument()
  })
})

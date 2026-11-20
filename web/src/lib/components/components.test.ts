import { fireEvent, render, screen } from '@testing-library/svelte'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { choiceQuestion, correctResult, numberQuestion, rangeQuestion, rangeResult, wrongResult } from '../../test/fixtures'
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

  it('shows the position for preflop questions', () => {
    render(QuestionView, { question: { ...numberQuestion, payload: { position: 'CO', hole: ['As', 'Kd'] } } })
    expect(screen.getByText('CO')).toBeInTheDocument()
  })

  it('shows fact chips such as the villain range or stack', () => {
    render(QuestionView, {
      question: { ...numberQuestion, payload: { facts: [{ label: 'Stack', value: '8bb' }, { label: 'Calls', value: 'top 30%' }] } },
    })
    expect(screen.getByText('8bb')).toBeInTheDocument()
    expect(screen.getByText('top 30%')).toBeInTheDocument()
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

  it('explains invalid input instead of silently ignoring it', async () => {
    const onsubmit = vi.fn()
    const user = userEvent.setup()
    render(AnswerInput, { question: numberQuestion, onsubmit })
    const input = screen.getByLabelText('Your answer')
    expect(screen.getByText('Enter to check · S to skip')).toBeInTheDocument()
    await user.type(input, 'lots{Enter}')
    expect(input).toHaveAttribute('aria-invalid', 'true')
    expect(screen.getByText('Type a number, like 25, 25% or 1/3.')).toBeInTheDocument()
    await user.clear(input)
    await user.type(input, '1/4{Enter}')
    expect(input).toHaveAttribute('aria-invalid', 'false')
    expect(onsubmit).toHaveBeenCalledWith(25)
  })

  it('drops the skip hint where skipping is not offered', () => {
    render(AnswerInput, { question: numberQuestion, onsubmit: vi.fn(), skippable: false })
    expect(screen.getByText('Enter to check')).toBeInTheDocument()
  })

  it('shows the choice shortcut hint', () => {
    render(AnswerInput, { question: choiceQuestion, onsubmit: vi.fn() })
    expect(screen.getByText('Press 1–3 to answer · S to skip')).toBeInTheDocument()
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

  it('ignores digits with modifier keys, held keys or typed into an input', async () => {
    const onsubmit = vi.fn()
    render(AnswerInput, { question: choiceQuestion, onsubmit })
    for (const init of [{ ctrlKey: true }, { metaKey: true }, { altKey: true }, { repeat: true }]) {
      await fireEvent.keyDown(window, { key: '1', ...init })
    }
    const field = document.createElement('input')
    document.body.appendChild(field)
    await fireEvent.keyDown(field, { key: '1' })
    field.remove()
    expect(onsubmit).not.toHaveBeenCalled()
  })

  it('focuses the choices, not a choice, so a second Enter after Next answers nothing', async () => {
    const onsubmit = vi.fn()
    render(AnswerInput, { question: choiceQuestion, onsubmit })
    const group = screen.getByRole('group', { name: 'Choices' })
    expect(group).toHaveFocus()
    await fireEvent.keyDown(group, { key: 'Enter' })
    expect(onsubmit).not.toHaveBeenCalled()
    // A held Enter on a choice does not press it again.
    const held = new KeyboardEvent('keydown', { key: 'Enter', repeat: true, bubbles: true, cancelable: true })
    screen.getAllByRole('button')[0].dispatchEvent(held)
    expect(held.defaultPrevented).toBe(true)
  })

  it('marks the answer after grading', () => {
    render(AnswerInput, {
      question: choiceQuestion,
      onsubmit: vi.fn(),
      answered: { response: 'Player 1', expected: 'Player 2' },
    })
    const [first, second, third] = screen.getAllByRole('button')
    expect(first).toHaveClass('wrong')
    expect(first).toHaveTextContent('✗')
    expect(second).toHaveClass('right')
    expect(second).toHaveTextContent('✓')
    expect(third).not.toHaveClass('right')
  })

  it('marks a correct choice once', () => {
    render(AnswerInput, {
      question: choiceQuestion,
      onsubmit: vi.fn(),
      answered: { response: 'Player 2', expected: 'Player 2' },
    })
    expect(screen.getByRole('button', { name: /Player 2/ })).toHaveClass('right')
    expect(screen.queryByText('✗')).toBeNull()
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

  it('shows the error, tolerance and closeness meter for a wrong numeric answer', () => {
    render(Feedback, { result: { ...wrongResult, tolerance: 1.5 }, unit: '%', onnext: vi.fn() })
    expect(screen.getByRole('heading')).toHaveTextContent('Not quite')
    expect(screen.getByText('(+5 pts)')).toBeInTheDocument()
    expect(screen.getByText('· answers within ±1.5 pts count')).toBeInTheDocument()
    expect(
      screen.getByRole('img', { name: 'Your estimate 30% against the answer 25%, accepted range ±1.5 points' }),
    ).toBeInTheDocument()
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
    expect(screen.getByText("Locked in. You'll see this drill again in 3 days.")).toBeInTheDocument()
  })

  it('reveals the chart for preflop answers', () => {
    const grid = Array.from({ length: 13 }, () => Array<string>(13).fill('Fold'))
    render(Feedback, {
      result: { ...wrongResult, reveal: { grid, hand: 'A9o', choices: ['Raise', 'Fold'] } },
      onnext: vi.fn(),
    })
    expect(screen.getByRole('grid', { name: 'Chart for this spot' })).toBeInTheDocument()
    expect(screen.getByRole('gridcell', { name: 'A9o: Fold' })).toHaveClass('hl')
    expect(screen.getAllByRole('listitem').map((li) => li.textContent?.trim())).toContain('Raise')
  })

  it('titles a revealed range', () => {
    const grid = Array.from({ length: 13 }, () => Array<string>(13).fill('Fold'))
    render(Feedback, { result: { ...wrongResult, reveal: { grid, label: 'BB calling range' } }, onnext: vi.fn() })
    expect(screen.getByRole('grid', { name: 'BB calling range' })).toBeInTheDocument()
  })

  it('reveals a chart even without listed choices', () => {
    const grid = Array.from({ length: 13 }, () => Array<string>(13).fill('Fold'))
    render(Feedback, { result: { ...wrongResult, reveal: { grid } }, onnext: vi.fn() })
    expect(screen.getByRole('grid')).toBeInTheDocument()
  })

  it('shows unitless numeric errors and exact-answer drills', () => {
    render(Feedback, { result: { ...wrongResult, error: -2, tolerance: 0 }, unit: 'outs', onnext: vi.fn() })
    expect(screen.getByText('(-2)')).toBeInTheDocument()
    expect(screen.getByText('· the exact number is needed')).toBeInTheDocument()
    expect(screen.queryByRole('img', { name: /Your estimate/ })).toBeNull()
  })

  it('words reviews by rating', () => {
    const due = new Date(Date.now() + 60_000).toISOString()
    const { unmount } = render(Feedback, { result: { ...wrongResult, review: { rating: 'again', due } }, onnext: vi.fn() })
    expect(screen.getByText('This drill comes back for another go in 1 minute.')).toBeInTheDocument()
    unmount()
    render(Feedback, { result: { ...wrongResult, review: { rating: 'hard', due } }, onnext: vi.fn() })
    expect(screen.getByText('Getting there. This drill comes back in 1 minute.')).toBeInTheDocument()
  })
})

describe('Range answers', () => {
  it('starts from every hand, edits, clears and locks in', async () => {
    const onsubmit = vi.fn()
    render(AnswerInput, { question: rangeQuestion, onsubmit })
    expect(screen.getByText('169 of 169 hand classes')).toBeInTheDocument()
    await fireEvent.click(screen.getByRole('button', { name: 'Clear' }))
    expect(screen.getByText('0 of 169 hand classes')).toBeInTheDocument()
    await fireEvent.pointerDown(screen.getByRole('gridcell', { name: 'AA' }))
    await fireEvent.pointerUp(window)
    await fireEvent.click(screen.getByRole('button', { name: 'Lock in' }))
    expect(onsubmit).toHaveBeenLastCalledWith(['AA'])
    await fireEvent.click(screen.getByRole('button', { name: 'All' }))
    expect(screen.getByText('169 of 169 hand classes')).toBeInTheDocument()
  })

  it('starts from the previous street and locks while graded', async () => {
    const onsubmit = vi.fn()
    render(AnswerInput, { question: rangeQuestion, onsubmit, startRange: ['AA', 'KK'], disabled: true })
    expect(screen.getByText('2 of 169 hand classes')).toBeInTheDocument()
    await fireEvent.pointerDown(screen.getByRole('gridcell', { name: 'QQ' }))
    expect(screen.getByText('2 of 169 hand classes')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Lock in' })).toBeDisabled()
  })
})

describe('Hand-reading view and feedback', () => {
  it('lists the action so far', () => {
    render(QuestionView, { question: rangeQuestion })
    expect(screen.getByRole('list', { name: 'Action so far' })).toHaveTextContent('Nit raises to 2.5bb')
  })

  it('shows the match, the best possible and the real range', () => {
    render(Feedback, { result: rangeResult, unit: '%', onnext: vi.fn() })
    expect(document.querySelector('.numbers')).toHaveTextContent('Range match 61.2% · best possible 82.5%')
    expect(screen.getByRole('grid', { name: "Nit's real range" })).toBeInTheDocument()
    expect(screen.getByRole('gridcell', { name: 'AA: 100%' })).toHaveClass('hl')
    expect(screen.getByText(/outlined cell is the hand it actually held/)).toBeInTheDocument()
    expect(screen.queryByRole('img', { name: /Your estimate/ })).toBeNull()
  })

  it('omits the actual hand before the last street', () => {
    render(Feedback, {
      result: { ...rangeResult, reveal: { ...rangeResult.reveal, hand: null, label: undefined } },
      unit: '%',
      onnext: vi.fn(),
    })
    expect(screen.getByRole('grid', { name: 'Real range' })).toBeInTheDocument()
    expect(screen.queryByText(/outlined cell/)).toBeNull()
  })
})

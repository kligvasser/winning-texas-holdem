import { fireEvent, render, screen } from '@testing-library/svelte'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { api } from '../api'
import { choiceQuestion, correctResult, drills, numberQuestion, wrongResult } from '../../test/fixtures'
import DrillRunner from './DrillRunner.svelte'

vi.mock('../api', () => ({ api: { question: vi.fn(), answer: vi.fn() } }))
const question = vi.mocked(api.question)
const answer = vi.mocked(api.answer)

beforeEach(() => {
  question.mockReset()
  answer.mockReset()
})

describe('DrillRunner', () => {
  it('runs a question, grades it and deals the next', async () => {
    question.mockResolvedValueOnce(numberQuestion).mockResolvedValueOnce(choiceQuestion)
    answer.mockResolvedValueOnce(correctResult).mockResolvedValueOnce(wrongResult)
    const user = userEvent.setup()
    render(DrillRunner, { drills, random: () => 0 })
    expect(screen.getByText('Dealing…')).toBeInTheDocument()
    await user.type(await screen.findByLabelText('Your answer'), '25{Enter}')
    expect(answer).toHaveBeenCalledWith('q1', 25, expect.any(Number))
    expect(await screen.findByText('Correct')).toBeInTheDocument()
    expect(screen.getByLabelText('Session score')).toHaveTextContent('1 / 1')
    expect(screen.getByText('Pot odds')).toBeInTheDocument()

    await fireEvent.click(screen.getByRole('button', { name: /Next/ }))
    expect(question).toHaveBeenLastCalledWith('pot-odds')
    await fireEvent.click(await screen.findByRole('button', { name: /Player 1/ }))
    expect(await screen.findByText('Not quite')).toBeInTheDocument()
    expect(screen.getByLabelText('Session score')).toHaveTextContent('1 / 2')
  })

  it('picks drills at random for mixed sessions', async () => {
    question.mockResolvedValue(choiceQuestion)
    render(DrillRunner, { drills, random: () => 0.99 })
    expect(await screen.findByText('Who wins?')).toBeInTheDocument()
    expect(question).toHaveBeenCalledWith('showdown')
  })

  it('uses Math.random by default', async () => {
    vi.spyOn(Math, 'random').mockReturnValue(0)
    question.mockResolvedValue(numberQuestion)
    render(DrillRunner, { drills })
    await screen.findByLabelText('Your answer')
    expect(question).toHaveBeenCalledWith('pot-odds')
  })

  it('shows errors and retries', async () => {
    question.mockRejectedValueOnce(new Error('server down')).mockResolvedValueOnce(numberQuestion)
    render(DrillRunner, { drills, random: () => 0 })
    expect(await screen.findByRole('alert')).toHaveTextContent('server down')
    await fireEvent.click(screen.getByRole('button', { name: 'Try again' }))
    expect(await screen.findByLabelText('Your answer')).toBeInTheDocument()
  })

  it('runs a fixed queue to the end', async () => {
    question.mockResolvedValueOnce(numberQuestion).mockResolvedValueOnce(choiceQuestion)
    answer.mockResolvedValueOnce(correctResult).mockResolvedValueOnce(wrongResult)
    const user = userEvent.setup()
    render(DrillRunner, { drills, queue: ['pot-odds', 'showdown'] })
    const bar = screen.getByRole('progressbar', { name: 'Session progress' })
    expect(bar).toHaveAttribute('aria-valuemax', '2')
    await user.type(await screen.findByLabelText('Your answer'), '25{Enter}')
    await fireEvent.click(await screen.findByRole('button', { name: /Next/ }))
    expect(question).toHaveBeenLastCalledWith('showdown')
    await fireEvent.click(await screen.findByRole('button', { name: /Player 1/ }))
    expect(bar).toHaveAttribute('aria-valuenow', '2')
    await fireEvent.click(await screen.findByRole('button', { name: /Next/ }))
    expect(await screen.findByRole('heading', { name: 'Session complete' })).toBeInTheDocument()
    expect(screen.getByText(/1 of 2 correct/)).toBeInTheDocument()
    expect(question).toHaveBeenCalledTimes(2)
  })

  it('reports answer failures', async () => {
    question.mockResolvedValue(choiceQuestion)
    answer.mockRejectedValue(new Error('question not found'))
    render(DrillRunner, { drills, random: () => 0 })
    await fireEvent.click(await screen.findByRole('button', { name: /Player 1/ }))
    expect(await screen.findByRole('alert')).toHaveTextContent('question not found')
  })
})

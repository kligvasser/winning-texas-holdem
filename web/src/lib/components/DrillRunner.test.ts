import { fireEvent, render, screen } from '@testing-library/svelte'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError, api } from '../api'
import { choiceQuestion, correctResult, drills, numberQuestion, wrongResult } from '../../test/fixtures'
import DrillRunner from './DrillRunner.svelte'

vi.mock('../api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../api')>()),
  api: { question: vi.fn(), answer: vi.fn() },
}))
const question = vi.mocked(api.question)
const answer = vi.mocked(api.answer)

const q = (id: string, base = choiceQuestion) => ({ ...base, id })

beforeEach(() => {
  question.mockReset()
  answer.mockReset()
})

describe('DrillRunner', () => {
  it('grades an answer, prefetches the next question and shows it instantly', async () => {
    question
      .mockResolvedValueOnce(numberQuestion)
      .mockResolvedValueOnce(choiceQuestion)
      .mockResolvedValue(q('later'))
    answer.mockResolvedValueOnce(correctResult).mockResolvedValueOnce(wrongResult)
    const user = userEvent.setup()
    render(DrillRunner, { drills, random: () => 0 })
    expect(screen.getByText('Dealing…')).toBeInTheDocument()
    await user.type(await screen.findByLabelText('Your answer'), '25%{Enter}')
    expect(answer).toHaveBeenCalledWith('q1', 25, expect.any(Number))
    expect(await screen.findByText('Correct')).toBeInTheDocument()
    expect(screen.getByLabelText('Session score')).toHaveTextContent('1/1 correct')
    expect(screen.getByText('Pot odds')).toBeInTheDocument()
    // The next question was already requested while the feedback is on screen.
    expect(question).toHaveBeenCalledTimes(2)
    expect(screen.queryByRole('button', { name: 'Skip' })).toBeNull()

    await fireEvent.click(screen.getByRole('button', { name: /Next/ }))
    await fireEvent.click(await screen.findByRole('button', { name: /Player 1/ }))
    expect(await screen.findByText('Not quite')).toBeInTheDocument()
    expect(screen.getByLabelText('Session score')).toHaveTextContent('1/2 correct')
    expect(question).toHaveBeenCalledTimes(3)
  })

  it('shows a combo after two correct answers in a row and resets it on a miss', async () => {
    question.mockImplementation(async () => q(crypto.randomUUID()))
    answer
      .mockResolvedValueOnce(correctResult)
      .mockResolvedValueOnce(correctResult)
      .mockResolvedValueOnce(wrongResult)
    render(DrillRunner, { drills, random: () => 0.99 })
    for (let i = 0; i < 3; i += 1) {
      await fireEvent.click(await screen.findByRole('button', { name: /Player 1/ }))
      await screen.findByRole('button', { name: /Next/ })
      if (i === 1) expect(screen.getByLabelText('Streak 2')).toHaveTextContent('🔥 2')
      await fireEvent.click(screen.getByRole('button', { name: /Next/ }))
    }
    expect(screen.queryByLabelText(/Streak/)).toBeNull()
  })

  it('skips with the button or the S key, but not while typing an answer', async () => {
    question
      .mockResolvedValueOnce(numberQuestion)
      .mockResolvedValueOnce(q('q2'))
      .mockResolvedValueOnce(q('q3', numberQuestion))
    render(DrillRunner, { drills, random: () => 0 })
    const input = await screen.findByLabelText('Your answer')
    await fireEvent.input(input, { target: { value: '12' } })
    await fireEvent.keyDown(input, { key: 's' })
    expect(question).toHaveBeenCalledTimes(1)
    await fireEvent.click(screen.getByRole('button', { name: 'Skip' }))
    await screen.findByRole('button', { name: /Player 1/ })
    await fireEvent.keyDown(window, { key: 'S' })
    expect(await screen.findByLabelText('Your answer')).toBeInTheDocument()
    expect(question).toHaveBeenCalledTimes(3)
    expect(answer).not.toHaveBeenCalled()
  })

  it('ends a free session on request with a summary, and plays again', async () => {
    question.mockImplementation(async () => q(crypto.randomUUID()))
    answer.mockResolvedValue(correctResult)
    render(DrillRunner, { drills, random: () => 0.99 })
    expect(screen.queryByRole('button', { name: 'End session' })).toBeNull()
    await fireEvent.click(await screen.findByRole('button', { name: /Player 1/ }))
    await fireEvent.click(await screen.findByRole('button', { name: /Next/ }))
    await fireEvent.click(await screen.findByRole('button', { name: 'End session' }))
    expect(screen.getByRole('heading', { name: 'Session complete' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Back to Math Lab' })).toHaveAttribute('href', '#/math-lab')
    // S does nothing on the summary.
    await fireEvent.keyDown(window, { key: 's' })
    await fireEvent.click(screen.getByRole('button', { name: 'Play again' }))
    expect(await screen.findByLabelText('Session score')).toHaveTextContent('0/0 correct')
    expect(await screen.findByRole('button', { name: /Player 1/ })).toBeInTheDocument()
  })

  it('finishes a queue whose last question was answered, and ignores S on feedback', async () => {
    question.mockResolvedValueOnce(choiceQuestion)
    answer.mockResolvedValueOnce(correctResult)
    render(DrillRunner, { drills, queue: ['showdown'] })
    await fireEvent.click(await screen.findByRole('button', { name: /Player 1/ }))
    await screen.findByRole('button', { name: /Next/ })
    await fireEvent.keyDown(window, { key: 's' })
    expect(screen.getByText('Correct')).toBeInTheDocument()
    await fireEvent.click(screen.getByRole('button', { name: /Next/ }))
    expect(await screen.findByRole('heading', { name: 'Session complete' })).toBeInTheDocument()
    expect(question).toHaveBeenCalledTimes(1)
  })

  it('runs a fixed queue to the end, counting skipped questions', async () => {
    question
      .mockResolvedValueOnce(numberQuestion)
      .mockResolvedValueOnce(choiceQuestion)
      .mockResolvedValueOnce(q('q3'))
    answer.mockResolvedValueOnce(correctResult)
    const user = userEvent.setup()
    render(DrillRunner, { drills, queue: ['pot-odds', 'showdown', 'showdown'] })
    const bar = screen.getByRole('progressbar', { name: 'Session progress' })
    expect(bar).toHaveAttribute('aria-valuemax', '3')
    await user.type(await screen.findByLabelText('Your answer'), '25{Enter}')
    expect(question).toHaveBeenLastCalledWith('showdown')
    await fireEvent.click(await screen.findByRole('button', { name: /Next/ }))
    await fireEvent.click(await screen.findByRole('button', { name: 'Skip' }))
    await fireEvent.click(await screen.findByRole('button', { name: 'Skip' }))
    expect(await screen.findByRole('heading', { name: 'Session complete' })).toBeInTheDocument()
    expect(bar).toHaveAttribute('aria-valuenow', '3')
    expect(screen.getByText('Skipped 2.')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Browse the curriculum' })).toHaveAttribute('href', '#/learn')
    expect(screen.queryByRole('button', { name: 'End session' })).toBeNull()
    expect(question).toHaveBeenCalledTimes(3)
  })

  it('plays a multi-street scenario as one item of a queue', async () => {
    const river = q('river')
    const turn = { ...q('turn'), prompt: 'Turn: call or fold?' }
    question.mockResolvedValueOnce({ ...q('pre'), prompt: 'Open or fold?' }).mockResolvedValue(q('other'))
    answer
      .mockResolvedValueOnce({ ...correctResult, follow_up: turn })
      .mockResolvedValueOnce({ ...wrongResult, follow_up: { ...river, prompt: 'River: bluff?' } })
      .mockResolvedValueOnce(correctResult)
    render(DrillRunner, { drills, queue: ['showdown', 'showdown'] })
    expect(await screen.findByText('Open or fold?')).toBeInTheDocument()
    await fireEvent.click(screen.getByRole('button', { name: /Player 1/ }))
    expect(await screen.findByRole('button', { name: /Next street/ })).toBeInTheDocument()
    expect(question).toHaveBeenCalledTimes(1) // no prefetch while the hand is still going
    await fireEvent.click(screen.getByRole('button', { name: /Next street/ }))
    expect(screen.getByText('Turn: call or fold?')).toBeInTheDocument()
    expect(screen.getByText('Question 1 of 2')).toBeInTheDocument()
    await fireEvent.click(screen.getByRole('button', { name: /Player 1/ }))
    await fireEvent.click(await screen.findByRole('button', { name: /Next street/ }))
    expect(screen.getByText('River: bluff?')).toBeInTheDocument()
    await fireEvent.click(screen.getByRole('button', { name: /Player 1/ }))
    // The last street finishes the item: the queue advances and the next item is prefetched.
    expect(await screen.findByRole('button', { name: /^Next ⏎/ })).toBeInTheDocument()
    expect(question).toHaveBeenCalledTimes(2)
    expect(screen.getByLabelText('Session score')).toHaveTextContent('2/3 correct')
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

  it('surfaces a failed prefetch when moving on', async () => {
    question.mockResolvedValueOnce(choiceQuestion).mockRejectedValueOnce(new Error('offline'))
    answer.mockResolvedValue(correctResult)
    render(DrillRunner, { drills, random: () => 0 })
    await fireEvent.click(await screen.findByRole('button', { name: /Player 1/ }))
    await fireEvent.click(await screen.findByRole('button', { name: /Next/ }))
    expect(await screen.findByRole('alert')).toHaveTextContent('offline')
  })

  it('keeps the question when sending fails, and retries the same answer', async () => {
    question.mockResolvedValue(choiceQuestion)
    answer.mockRejectedValueOnce(new Error('Failed to fetch')).mockResolvedValueOnce(correctResult)
    render(DrillRunner, { drills, random: () => 0 })
    await fireEvent.click(await screen.findByRole('button', { name: /Player 2/ }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Could not send your answer: Failed to fetch')
    expect(screen.getByText('Which player wins?')).toBeInTheDocument()
    await fireEvent.click(screen.getByRole('button', { name: 'Retry' }))
    expect(await screen.findByText('Correct')).toBeInTheDocument()
    expect(answer).toHaveBeenLastCalledWith('q2', 'Player 2', expect.any(Number))
    expect(screen.queryByRole('alert')).toBeNull()
  })

  it('replaces a question the server has forgotten', async () => {
    question.mockResolvedValueOnce(choiceQuestion).mockResolvedValueOnce(q('fresh', numberQuestion))
    answer.mockRejectedValueOnce(new ApiError(404, 'question not found or already answered'))
    render(DrillRunner, { drills, random: () => 0 })
    await fireEvent.click(await screen.findByRole('button', { name: /Player 1/ }))
    expect(await screen.findByLabelText('Your answer')).toBeInTheDocument()
    expect(screen.getByRole('alert')).toHaveTextContent('This question expired')
    expect(screen.queryByRole('button', { name: 'Retry' })).toBeNull()
  })

  it('resumes saved progress and reports progress after each step', async () => {
    question.mockResolvedValue(choiceQuestion)
    answer.mockResolvedValue(correctResult)
    const onprogress = vi.fn()
    render(DrillRunner, {
      drills,
      queue: ['pot-odds', 'showdown', 'showdown'],
      resume: { position: 1, results: [{ drill: 'pot-odds', correct: true, ms: 1000 }], skipped: 0 },
      onprogress,
    })
    expect(await screen.findByText('Question 2 of 3')).toBeInTheDocument()
    expect(screen.getByLabelText('Session score')).toHaveTextContent('1/1 correct')
    expect(question).toHaveBeenCalledWith('showdown')
    await fireEvent.click(await screen.findByRole('button', { name: /Player 1/ }))
    expect(onprogress).toHaveBeenLastCalledWith(expect.objectContaining({ position: 2, skipped: 0 }))
    await fireEvent.click(await screen.findByRole('button', { name: /Next/ }))
    await fireEvent.click(await screen.findByRole('button', { name: 'Skip' }))
    expect(onprogress).toHaveBeenLastCalledWith(expect.objectContaining({ position: 3, skipped: 1 }))
  })
})

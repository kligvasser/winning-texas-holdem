import { fireEvent, render, screen, waitFor } from '@testing-library/svelte'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { api } from '../api'
import { choiceQuestion, correctResult, drills, wrongResult } from '../../test/fixtures'
import SpeedRound from './SpeedRound.svelte'

vi.mock('../api', () => ({ api: { question: vi.fn(), answer: vi.fn() } }))
const question = vi.mocked(api.question)
const answer = vi.mocked(api.answer)

let clock = 0
const now = () => clock
let counter = 0

beforeEach(() => {
  clock = 1_000
  counter = 0
  localStorage.clear()
  question.mockReset()
  answer.mockReset()
  question.mockImplementation(async () => ({ ...choiceQuestion, id: `q${(counter += 1)}` }))
})

afterEach(() => localStorage.clear())

const props = { drills, roundKey: 'mixed', seconds: 10, now, random: () => 0, flashMs: 5 }

async function choose(name: RegExp) {
  await waitFor(() => expect(screen.getByRole('button', { name })).toBeEnabled())
  await fireEvent.click(screen.getByRole('button', { name }))
}

describe('SpeedRound', () => {
  it('runs a round: correct answers advance instantly and score', async () => {
    answer.mockResolvedValue(correctResult)
    render(SpeedRound, props)
    expect(screen.getByText('Personal best:', { exact: false })).toHaveTextContent('Personal best: 0')
    await fireEvent.click(screen.getByRole('button', { name: /Start/ }))
    expect(screen.getByLabelText('Seconds left')).toHaveTextContent('10s')
    expect(await screen.findByText('Press 1–3 to answer')).toBeInTheDocument()
    await choose(/Player 1/)
    await waitFor(() => expect(screen.getByLabelText('Speed score')).toHaveTextContent('⚡ 1'))
    await choose(/Player 1/)
    await waitFor(() => expect(screen.getByLabelText('Speed score')).toHaveTextContent('⚡ 2'))
    expect(question).toHaveBeenCalledWith('pot-odds')

    clock += 10_000
    expect(await screen.findByRole('heading', { name: 'New personal best!' })).toBeInTheDocument()
    expect(screen.getByText('correct of 2', { exact: false })).toBeInTheDocument()
    expect(localStorage.getItem('holdem.speed.mixed')).toBe('2')
  })

  it('shows the answer briefly after a miss, then moves on', async () => {
    answer.mockResolvedValueOnce({ ...wrongResult, expected: 'Player 2', response: 'Player 1' })
    render(SpeedRound, props)
    await fireEvent.click(screen.getByRole('button', { name: /Start/ }))
    await choose(/Player 1/)
    expect(await screen.findByRole('status')).toHaveTextContent('Answer: Player 2')
    await waitFor(() => expect(screen.queryByRole('status')).toBeNull())
    expect(screen.getByLabelText('Speed score')).toHaveTextContent('⚡ 0')
  })

  it("does not count a score that does not beat the best, and Enter replays", async () => {
    localStorage.setItem('holdem.speed.mixed', '5')
    render(SpeedRound, props)
    expect(screen.getByText(/Personal best/)).toHaveTextContent('5')
    await fireEvent.keyDown(window, { key: 'Enter' })
    expect(await screen.findByLabelText('Seconds left')).toBeInTheDocument()
    await fireEvent.keyDown(window, { key: 'Enter' }) // ignored while running
    clock += 10_000
    expect(await screen.findByRole('heading', { name: "Time's up" })).toBeInTheDocument()
    expect(document.querySelector('.confetti')).toBeNull()
    await fireEvent.click(screen.getByRole('button', { name: 'Play again' }))
    expect(await screen.findByLabelText('Seconds left')).toBeInTheDocument()
  })

  it('stops with a message when the server fails', async () => {
    question.mockRejectedValue(new Error('offline'))
    render(SpeedRound, props)
    await fireEvent.click(screen.getByRole('button', { name: /Start/ }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Stopped early: offline')
  })

  it('stops when an answer cannot be sent, and ignores answers after time is up', async () => {
    answer.mockRejectedValueOnce(new Error('offline'))
    const first = render(SpeedRound, props)
    await fireEvent.click(screen.getByRole('button', { name: /Start/ }))
    await choose(/Player 1/)
    expect(await screen.findByRole('alert')).toHaveTextContent('Stopped early: offline')
    first.unmount()

    let release: (value: typeof correctResult) => void = () => {}
    answer.mockImplementationOnce(() => new Promise((resolve) => (release = resolve)))
    render(SpeedRound, props)
    await fireEvent.click(screen.getByRole('button', { name: /Start/ }))
    await choose(/Player 1/)
    await fireEvent.click(screen.getByRole('button', { name: /Player 2/ })) // busy: ignored
    clock += 10_000
    await screen.findByRole('heading', { name: "Time's up" })
    release(correctResult)
    await Promise.resolve()
    expect(screen.getByText('correct of 0', { exact: false })).toBeInTheDocument()
    expect(answer).toHaveBeenCalledTimes(2)
  })

  it('stops flashing a miss if time runs out meanwhile', async () => {
    answer.mockResolvedValueOnce(wrongResult)
    render(SpeedRound, { ...props, flashMs: 200 })
    await fireEvent.click(screen.getByRole('button', { name: /Start/ }))
    await choose(/Player 1/)
    await screen.findByRole('status')
    clock += 10_000
    await screen.findByRole('heading', { name: "Time's up" })
    await new Promise((r) => setTimeout(r, 250))
    expect(screen.getByRole('heading', { name: "Time's up" })).toBeInTheDocument()
  })

  it('uses the real clock and randomness by default', async () => {
    answer.mockResolvedValue(correctResult)
    render(SpeedRound, { drills, roundKey: 'x' })
    await fireEvent.click(screen.getByRole('button', { name: /Start/ }))
    expect(await screen.findByLabelText('Seconds left')).toHaveTextContent('60s')
  })
})

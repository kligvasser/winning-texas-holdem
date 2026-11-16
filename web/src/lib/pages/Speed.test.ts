import { fireEvent, render, screen } from '@testing-library/svelte'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { api } from '../api'
import { drills } from '../../test/fixtures'
import Speed from './Speed.svelte'

vi.mock('../api', () => ({ api: { drills: vi.fn(), question: vi.fn(), answer: vi.fn() } }))
const mocked = vi.mocked(api)

const speedy = drills.map((d) => ({ ...d, speed: d.key === 'showdown' }))

beforeEach(() => {
  vi.resetAllMocks()
  mocked.drills.mockResolvedValue(speedy)
})

describe('Speed page', () => {
  it('offers a mixed round of speed drills by default', async () => {
    render(Speed)
    expect(screen.getByText('Loading…')).toBeInTheDocument()
    expect(await screen.findByRole('heading', { name: /60-second speed round/ })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Mixed' })).toHaveAttribute('aria-current', 'page')
    expect(screen.getByRole('link', { name: 'Who wins?' })).toHaveAttribute('href', '#/speed/showdown')
    expect(screen.queryByRole('link', { name: 'Pot odds' })).toBeNull()
  })

  it('runs a single drill', async () => {
    mocked.question.mockReturnValue(new Promise(() => {}))
    render(Speed, { selected: 'showdown' })
    expect(await screen.findByRole('heading', { name: 'Speed round: Who wins?' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Who wins?' })).toHaveAttribute('aria-current', 'page')
    await fireEvent.click(screen.getByRole('button', { name: /Start/ }))
    expect(mocked.question).toHaveBeenCalledWith('showdown')
  })

  it('explains drills without a speed round', async () => {
    render(Speed, { selected: 'pot-odds' })
    expect(await screen.findByText(/has no speed round/)).toBeInTheDocument()
  })

  it('reports load failures', async () => {
    mocked.drills.mockRejectedValue(new Error('offline'))
    render(Speed)
    expect(await screen.findByRole('alert')).toHaveTextContent('Could not load drills: offline')
  })

  it('hides the round list when nothing qualifies', async () => {
    mocked.drills.mockResolvedValue(drills.map((d) => ({ ...d, speed: false })))
    render(Speed)
    expect(await screen.findByText(/has no speed round/)).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Other rounds' })).toBeNull()
  })
})

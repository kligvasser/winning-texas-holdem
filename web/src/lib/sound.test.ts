import { afterEach, describe, expect, it, vi } from 'vitest'
import { handView } from '../test/fixtures'
import { play, setSound, soundFor, soundOn } from './sound'

afterEach(() => {
  localStorage.clear()
  vi.unstubAllGlobals()
})

function fakeAudio() {
  const started: number[] = []
  const node = () => ({
    type: '',
    frequency: { value: 0 },
    gain: { setValueAtTime: vi.fn(), exponentialRampToValueAtTime: vi.fn() },
    connect: vi.fn(),
    start: (at: number) => started.push(at),
    stop: vi.fn(),
  })
  const built = vi.fn()
  const resumed = vi.fn()
  class Audio {
    currentTime = 2
    destination = {}
    state = 'suspended'
    resume = () => {
      resumed()
      this.state = 'running'
      return Promise.resolve()
    }
    constructor() {
      built()
    }
    createOscillator = node
    createGain = node
  }
  vi.stubGlobal('AudioContext', Audio)
  return { started, built, resumed }
}

describe('sound', () => {
  it('stays silent where the browser has no audio', () => {
    expect(play('chip')).toBe(false)
  })

  it('plays notes through one shared audio context, unless muted', () => {
    const { started, built, resumed } = fakeAudio()
    expect(soundOn()).toBe(true)
    expect(play('win')).toBe(true)
    expect(started).toHaveLength(4)
    expect(started[0]).toBe(2)
    expect(play('chip')).toBe(true)
    expect(built).toHaveBeenCalledTimes(1)
    expect(resumed).toHaveBeenCalledTimes(1) // woken once, then left running
    setSound(false)
    expect(soundOn()).toBe(false)
    expect(play('chip')).toBe(false)
    setSound(true)
    expect(play('fold')).toBe(true)
  })

  it('wakes the audio from a click, and schedules nothing while it is still asleep', async () => {
    vi.resetModules()
    const fresh = await import('./sound')
    const started: number[] = []
    const resumed = vi.fn()
    class Asleep {
      currentTime = 0
      state = 'suspended'
      resume = () => {
        resumed()
        return Promise.resolve()
      }
      createOscillator = () => ({ start: () => started.push(0) })
    }
    vi.stubGlobal('AudioContext', Asleep)
    expect(fresh.unlock()).toBeInstanceOf(Asleep)
    expect(resumed).toHaveBeenCalledTimes(1)
    expect(fresh.play('win')).toBe(false)
    expect(started).toEqual([])
    fresh.setSound(false)
    expect(fresh.unlock()).toBeUndefined()
  })

  it('copes with storage that is unavailable', () => {
    const broken = {
      getItem: () => {
        throw new Error('denied')
      },
      setItem: () => {
        throw new Error('denied')
      },
    } as unknown as Storage
    expect(soundOn(broken)).toBe(true)
    setSound(false, broken)
  })

  it('picks a sound for each kind of action', () => {
    const last = handView().last
    const frame = (kind: string, behind = 100) =>
      handView({ last: { ...last, kind, player: 1 }, behind: [200, behind, 200, 200, 200, 200] })
    expect(soundFor(frame('fold'))).toBe('fold')
    expect(soundFor(frame('check'))).toBe('check')
    expect(soundFor(frame('call'))).toBe('chip')
    expect(soundFor(frame('raise', 0))).toBe('allin')
    expect(soundFor(frame('post', 0))).toBe('chip')
  })
})

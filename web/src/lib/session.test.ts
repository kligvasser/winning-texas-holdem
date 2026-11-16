import { afterEach, describe, expect, it } from 'vitest'
import { loadSession, saveSession } from './session'

const session = { day: '2026-11-16', queue: ['a', 'b'], progress: { position: 1, results: [], skipped: 0 } }

afterEach(() => sessionStorage.clear())

describe('saved daily sessions', () => {
  it('round-trips through sessionStorage for the same day only', () => {
    saveSession(session)
    expect(loadSession('2026-11-16')).toEqual(session)
    expect(loadSession('2026-11-17')).toBeNull()
    saveSession(null)
    expect(loadSession('2026-11-16')).toBeNull()
  })

  it('survives corrupt data and unavailable storage', () => {
    sessionStorage.setItem('holdem.today', '{oops')
    expect(loadSession('2026-11-16')).toBeNull()
    const broken = {
      getItem: () => {
        throw new Error('denied')
      },
      setItem: () => {
        throw new Error('denied')
      },
      removeItem: () => {},
    } as unknown as Storage
    expect(loadSession('2026-11-16', broken)).toBeNull()
    expect(() => saveSession(session, broken)).not.toThrow()
  })
})

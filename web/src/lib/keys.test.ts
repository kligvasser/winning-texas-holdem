import { describe, expect, it } from 'vitest'
import { ignoreHeld } from './keys'

function press(key: string, repeat: boolean): KeyboardEvent {
  const event = new KeyboardEvent('keydown', { key, repeat, cancelable: true })
  ignoreHeld(event)
  return event
}

describe('ignoreHeld', () => {
  it('cancels a held Enter or Space', () => {
    expect(press('Enter', true).defaultPrevented).toBe(true)
    expect(press(' ', true).defaultPrevented).toBe(true)
  })

  it('leaves first presses and other keys alone', () => {
    expect(press('Enter', false).defaultPrevented).toBe(false)
    expect(press('a', true).defaultPrevented).toBe(false)
  })
})

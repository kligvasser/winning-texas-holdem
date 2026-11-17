/** Small synthesised table sounds: no audio files, and a mute switch kept in this browser. */

import type { TableView } from './api'

const KEY = 'holdem.sound'

/** One note: frequency (Hz), length (s), wave shape, and delay before it starts (s). */
type Note = [number, number, OscillatorType, number]

const SOUNDS = {
  chip: [
    [1800, 0.04, 'triangle', 0],
    [2400, 0.05, 'triangle', 0.035],
  ],
  check: [[240, 0.05, 'sine', 0]],
  fold: [[170, 0.12, 'sine', 0]],
  allin: [
    [330, 0.12, 'sawtooth', 0],
    [440, 0.12, 'sawtooth', 0.1],
    [660, 0.28, 'sawtooth', 0.2],
  ],
  win: [
    [523, 0.12, 'triangle', 0],
    [659, 0.12, 'triangle', 0.11],
    [784, 0.12, 'triangle', 0.22],
    [1047, 0.32, 'triangle', 0.33],
  ],
  lose: [
    [300, 0.2, 'sine', 0],
    [220, 0.36, 'sine', 0.18],
  ],
} satisfies Record<string, Note[]>

export type Sound = keyof typeof SOUNDS

let context: AudioContext | undefined

export function soundOn(storage: Storage = localStorage): boolean {
  try {
    return storage.getItem(KEY) !== 'off'
  } catch {
    return true
  }
}

export function setSound(on: boolean, storage: Storage = localStorage): void {
  try {
    storage.setItem(KEY, on ? 'on' : 'off')
  } catch {
    // Storage unavailable: the choice lasts until the page reloads.
  }
}

/** Play a sound if sound is on and this browser can make one. */
export function play(name: Sound, storage: Storage = localStorage): boolean {
  const Audio = (globalThis as { AudioContext?: typeof AudioContext }).AudioContext
  if (!Audio || !soundOn(storage)) return false
  context ??= new Audio()
  // Browsers start audio suspended until the page has been clicked.
  if (context.state === 'suspended') void context.resume()
  const now = context.currentTime
  for (const [frequency, length, shape, delay] of SOUNDS[name] as Note[]) {
    const oscillator = context.createOscillator()
    const gain = context.createGain()
    oscillator.type = shape
    oscillator.frequency.value = frequency
    gain.gain.setValueAtTime(0.07, now + delay)
    gain.gain.exponentialRampToValueAtTime(0.0001, now + delay + length)
    oscillator.connect(gain)
    gain.connect(context.destination)
    oscillator.start(now + delay)
    oscillator.stop(now + delay + length)
  }
  return true
}

/** The sound for the action that produced a table position. */
export function soundFor(frame: TableView): Sound {
  const { kind, player } = frame.last
  if (kind === 'fold') return 'fold'
  if (kind === 'check') return 'check'
  return kind !== 'post' && frame.behind[player] === 0 ? 'allin' : 'chip'
}

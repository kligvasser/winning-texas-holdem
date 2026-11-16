import { describe, expect, it } from 'vitest'
import { parseAnswer } from './answer'

describe('parseAnswer', () => {
  it.each([
    ['25', '', 25],
    ['25%', '%', 25],
    [' 25 % ', '%', 25],
    ['0,25', '', 0.25],
    ['-3', '', -3],
    ['1/3', '%', 33.33],
    ['1/4', '', 0.25],
    ['2 / 5', '%', 40],
  ])('%s (%s) is %s', (text, unit, value) => {
    expect(parseAnswer(text, unit)).toBe(value)
  })

  it.each(['', '   ', 'abc', '1/0', 'Infinity', '1/', '%'])('rejects %j', (text) => {
    expect(parseAnswer(text, '%')).toBeNull()
  })

  it('defaults to no unit', () => {
    expect(parseAnswer('1/2')).toBe(0.5)
  })
})

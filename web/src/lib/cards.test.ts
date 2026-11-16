import { describe, expect, it } from 'vitest'
import { parseCard } from './cards'

describe('parseCard', () => {
  it('parses rank, suit and names', () => {
    expect(parseCard('As')).toEqual({ code: 'As', rank: 'A', suit: 's', symbol: '♠', name: 'Ace of spades' })
    expect(parseCard('td')).toMatchObject({ code: 'Td', rank: '10', symbol: '♦', name: 'Ten of diamonds' })
  })

  it.each(['A', 'Asx', '1s', 'Ax'])('rejects %s', (code) => {
    expect(() => parseCard(code)).toThrow('invalid card')
  })
})

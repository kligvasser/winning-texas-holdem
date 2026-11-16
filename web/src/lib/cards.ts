export type Suit = 'c' | 'd' | 'h' | 's'

export interface CardFace {
  code: string
  rank: string
  suit: Suit
  symbol: string
  name: string
}

const SUIT_SYMBOLS: Record<Suit, string> = { c: '♣', d: '♦', h: '♥', s: '♠' }
const SUIT_NAMES: Record<Suit, string> = { c: 'clubs', d: 'diamonds', h: 'hearts', s: 'spades' }
const RANK_NAMES: Record<string, string> = {
  '2': 'Two',
  '3': 'Three',
  '4': 'Four',
  '5': 'Five',
  '6': 'Six',
  '7': 'Seven',
  '8': 'Eight',
  '9': 'Nine',
  T: 'Ten',
  J: 'Jack',
  Q: 'Queen',
  K: 'King',
  A: 'Ace',
}

/** Parse a two-character card code such as "As" or "Td". */
export function parseCard(code: string): CardFace {
  const rank = code.charAt(0).toUpperCase()
  const suit = code.charAt(1).toLowerCase() as Suit
  if (code.length !== 2 || !(rank in RANK_NAMES) || !(suit in SUIT_SYMBOLS)) {
    throw new Error(`invalid card ${code}`)
  }
  return {
    code: rank + suit,
    rank: rank === 'T' ? '10' : rank,
    suit,
    symbol: SUIT_SYMBOLS[suit],
    name: `${RANK_NAMES[rank]} of ${SUIT_NAMES[suit]}`,
  }
}

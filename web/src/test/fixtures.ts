import type { Activity, Concept, Curriculum, HandView, Legal, PlayState, ReviewedDecision, DailyPlan, DrillMeta, DrillStats, GradeResult, Question, Spot, SpotLeak } from '../lib/api'

export const drills: DrillMeta[] = [
  { key: 'pot-odds', title: 'Pot odds', concept: 'pot-odds', tier: 1, description: 'Need?' },
  { key: 'showdown', title: 'Who wins?', concept: 'board-reading', tier: 0, description: 'Pick' },
]

export const numberQuestion: Question = {
  id: 'q1',
  drill: 'pot-odds',
  concept: 'pot-odds',
  prompt: 'What equity do you need?',
  kind: 'number',
  payload: { pot: 100, bet: 50, hole: ['As', 'Kd'], villain: ['Qh', 'Qc'], board: ['2c', '7d', 'Th'] },
  choices: [],
  unit: '%',
}

export const choiceQuestion: Question = {
  id: 'q2',
  drill: 'showdown',
  concept: 'board-reading',
  prompt: 'Which player wins?',
  kind: 'choice',
  payload: { board: ['2c', '7d', 'Th', 'Js', '3h'], players: [['As', 'Kd'], ['Qh', 'Qc']] },
  choices: ['Player 1', 'Player 2', 'Split pot'],
  unit: '',
}

export const correctResult: GradeResult = {
  correct: true,
  expected: 25,
  response: 25,
  error: 0,
  explanation: ['bet / (pot + 2 x bet) = 25%.'],
  highlight: ['As'],
}

export const wrongResult: GradeResult = {
  correct: false,
  expected: 25,
  response: 30,
  error: 5,
  explanation: ['You overestimated.'],
  highlight: [],
}

export const stats: DrillStats[] = [
  { drill: 'pot-odds', attempts: 4, correct: 3, accuracy: 0.75, mean_abs_error: 2, bias: 1.5, mean_ms: 2500 },
  { drill: 'showdown', attempts: 2, correct: 1, accuracy: 0.5, mean_abs_error: null, bias: null, mean_ms: null },
  { drill: 'retired', attempts: 2, correct: 2, accuracy: 1, mean_abs_error: 1, bias: -1, mean_ms: 900 },
]

export const plan: DailyPlan = {
  due: ['pot-odds'],
  new: ['showdown'],
  extra: [],
  queue: ['pot-odds', 'showdown'],
}

const concept = (over: Partial<Concept>): Concept => ({
  id: 'x',
  title: 'X',
  tier: 0,
  summary: 'Summary',
  points: ['A point'],
  prerequisites: [],
  lectures: [{ label: '2016 L1 · Overview', url: 'https://ocw.mit.edu/courses/15-s50-x/' }],
  drills: [],
  attempts: 0,
  mastery: 0.5,
  status: 'new',
  ...over,
})

export const curriculum: Curriculum = {
  concepts: [
    concept({ id: 'board-reading', title: 'Reading the board', drills: ['showdown'], attempts: 12, mastery: 0.9, status: 'mastered' }),
    concept({ id: 'pot-odds', title: 'Pot odds and EV', tier: 1, drills: ['pot-odds', 'unlisted'], prerequisites: ['board-reading', 'ghost'], attempts: 3, mastery: 0.6, status: 'learning' }),
    concept({ id: 'icm', title: 'Push/fold and ICM', tier: 6 }),
  ],
  cards: {},
  materials: [{ label: '2016 lecture slides', url: 'https://ocw.mit.edu/slides' }],
}

const fold13 = (): string[] => Array<string>(13).fill('Fold')
export const utgGrid: string[][] = Array.from({ length: 13 }, (_, r) =>
  r === 0 ? ['Raise', 'Raise', ...Array<string>(11).fill('Fold')] : fold13(),
)

export const spots: Spot[] = [
  {
    id: 'utg-open',
    position: 'UTG',
    situation: 'Folded to you under the gun.',
    kind: 'open',
    choices: ['Raise', 'Fold'],
    note: 'Tight up front.',
    source: 'Baseline chart (self-authored, not solver output)',
    grid: utgGrid,
    frequencies: { Raise: 0.19, Fold: 0.81 },
  },
  {
    id: 'bb-vs-btn',
    position: 'BB',
    situation: 'The button opens.',
    kind: 'defend',
    choices: ['3-bet', 'Call', 'Fold'],
    note: 'Defend wide.',
    source: 'Baseline chart (self-authored, not solver output)',
    grid: utgGrid,
    frequencies: { '3-bet': 0.06, Call: 0.44, Fold: 0.5 },
  },
]

export const leaks: SpotLeak[] = [
  { spot: 'utg-open', position: 'UTG', situation: 'Folded to you under the gun.', attempts: 4, correct: 1, accuracy: 0.25, missed_hands: [{ hand: 'A9o', count: 2 }] },
  { spot: 'bb-vs-btn', position: 'BB', situation: 'The button opens.', attempts: 2, correct: 2, accuracy: 1, missed_hands: [] },
]

export const activity: Activity = {
  today: '2026-11-16',
  answered_today: 8,
  correct_today: 6,
  practiced_today: true,
  streak: 4,
  best_streak: 6,
  total: 144,
  history: [
    { date: '2026-11-11', answers: 0, correct: 0 },
    { date: '2026-11-12', answers: 3, correct: 2 },
    { date: '2026-11-13', answers: 40, correct: 30 },
  ],
}

export const handView = (over: Partial<HandView> = {}): HandView => ({
  street: 'flop',
  button: 0,
  board: ['Kh', '7d', '2c'],
  hole: [['As', 'Kd'], null],
  behind: [190, 186],
  bets: [0, 4],
  pot: 24,
  current: 0,
  finished: false,
  showdown: false,
  net: null,
  log: [
    { street: 'preflop', player: 0, kind: 'post', amount: 1, to: 1, pot: 0, to_call: 0 },
    { street: 'preflop', player: 1, kind: 'post', amount: 2, to: 2, pot: 1, to_call: 0 },
    { street: 'preflop', player: 0, kind: 'raise', amount: 4, to: 5, pot: 3, to_call: 1 },
  ],
  ...over,
})

export const legal: Legal = { to_call: 4, can_check: false, can_raise: true, min_raise_to: 8, max_raise_to: 190 }

export const decisions: ReviewedDecision[] = [
  { index: 2, street: 'preflop', board: [], action: 'raise', amount_bb: 2.5, pot_bb: 1.5, to_call_bb: 0.5, equity: 0.6, range_share: 1, need: 0.25, loss_bb: 0, verdict: 'info', note: 'Raises are not graded.' },
  { index: 5, street: 'flop', board: ['Kh', '7d', '2c'], action: 'fold', amount_bb: 0, pot_bb: 12, to_call_bb: 2, equity: 0.7, range_share: 0.5, need: 0.14, loss_bb: 7.8, verdict: 'mistake', note: 'You folded a winner.' },
  { index: 7, street: 'turn', board: [], action: 'call', amount_bb: 3, pot_bb: 12, to_call_bb: 3, equity: 0.3, range_share: 0.5, need: 0.2, loss_bb: 0.4, verdict: 'leak', note: 'Thin.' },
  { index: 9, street: 'river', board: [], action: 'call', amount_bb: 1, pot_bb: 12, to_call_bb: 1, equity: 0.5, range_share: 0.5, need: 0.1, loss_bb: 0, verdict: 'good', note: 'Fine.' },
]

export const playState = (over: Partial<PlayState> = {}): PlayState => ({
  id: 's1',
  style: { key: 'maniac', name: 'Maniac', blurb: 'Raises constantly.' },
  hand: handView(),
  legal,
  hands_played: 0,
  net_bb: 0,
  decisions: [],
  ...over,
})

const heat = Array.from({ length: 13 }, (_, r) => Array.from({ length: 13 }, (_, c) => (r === 0 && c === 0 ? 1 : r === 0 ? 0.4 : 0)))

export const rangeQuestion: Question = {
  id: 'r1',
  drill: 'hand-reading',
  concept: 'hand-reading',
  prompt: 'After the flop: which hands can Nit have?',
  kind: 'range',
  payload: {
    hole: ['7s', '2d'],
    board: ['Kh', '7d', '2c'],
    lines: ['Preflop: Nit raises to 2.5bb', 'Preflop: You call 1.5bb'],
    facts: [{ label: 'Villain', value: 'Nit on the button' }],
  },
  choices: [],
  unit: '%',
}

export const rangeResult: GradeResult = {
  correct: false,
  expected: 82.5,
  response: 61.2,
  error: null,
  explanation: ['Your range matched 61% of Nit’s real range; the best possible is 83%.'],
  highlight: ['As', 'Ad'],
  reveal: { weights: heat, hand: 'AA', label: "Nit's real range" },
}

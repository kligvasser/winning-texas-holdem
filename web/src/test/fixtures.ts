import type { DrillMeta, DrillStats, GradeResult, Question } from '../lib/api'

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

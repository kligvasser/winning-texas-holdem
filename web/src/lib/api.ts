export interface DrillMeta {
  key: string
  title: string
  concept: string
  tier: number
  description: string
  /** Quick multiple choice: offered in 60-second speed rounds. */
  speed?: boolean
}

export interface QuestionPayload {
  hole?: string[]
  villain?: string[]
  board?: string[]
  players?: string[][]
  pot?: number
  bet?: number
  /** Extra context shown as chips: villain range, stack, street, stacks and payouts... */
  facts?: { label: string; value: string }[]
  /** The action so far, one line per action (hand reading). */
  lines?: string[]
  [key: string]: unknown
}

export interface Question {
  id: string
  drill: string
  concept: string
  prompt: string
  kind: 'number' | 'choice' | 'range'
  payload: QuestionPayload
  choices: string[]
  unit: string
}

export interface Review {
  rating: 'again' | 'hard' | 'good' | 'easy'
  due: string
}

export interface GradeResult {
  tolerance?: number
  correct: boolean
  expected: number | string
  response: number | string
  error: number | null
  explanation: string[]
  highlight: string[]
  review?: Review | null
  /** The next step of a multi-street scenario, already issued by the server. */
  follow_up?: Question | null
  reveal?: {
    grid?: string[][]
    hand?: string | null
    choices?: string[]
    label?: string
    /** Hand reading: how likely each grid cell is (0-1), for a heat map. */
    weights?: number[][]
  }
}

export interface Spot {
  id: string
  position: string
  situation: string
  kind: 'open' | 'defend'
  choices: string[]
  note: string
  source: string
  grid: string[][]
  frequencies: Record<string, number>
}

export interface PaintResult {
  correct: string[]
  missed: string[]
  extra: string[]
  combos_wrong: number
  accuracy: number
}

export interface SpotLeak {
  spot: string
  position: string
  situation: string
  attempts: number
  correct: number
  accuracy: number
  missed_hands: { hand: string; count: number }[]
}

export interface DailyPlan {
  due: string[]
  new: string[]
  extra: string[]
  queue: string[]
}

export interface Lecture {
  label: string
  url: string
}

export interface Concept {
  id: string
  title: string
  tier: number
  summary: string
  points: string[]
  prerequisites: string[]
  lectures: Lecture[]
  drills: string[]
  attempts: number
  mastery: number
  status: 'new' | 'learning' | 'mastered'
}

export interface CardState {
  due: string | null
  is_due: boolean
  recall: number | null
}

export interface Curriculum {
  concepts: Concept[]
  cards: Record<string, CardState>
  materials: Lecture[]
}

export interface Activity {
  today: string
  answered_today: number
  correct_today: number
  practiced_today: boolean
  streak: number
  best_streak: number
  total: number
  history: { date: string; answers: number; correct: number }[]
}

export interface PlayStyle {
  key: string
  name: string
  /** The bot's name at the table ("Rocky"). */
  character: string
  blurb: string
}

export interface LoggedAction {
  street: string
  player: number
  kind: string
  amount: number
  to: number
  pot: number
  to_call: number
}

/** The table after one action. Seat 0 is you; the others sit clockwise. */
export interface TableView {
  street: string
  button: number
  positions: string[]
  board: string[]
  hole: (string[] | null)[]
  /** What each visible hand holds in words ("Two Pair"), once there is a flop. */
  made: (string | null)[]
  behind: number[]
  bets: number[]
  folded: boolean[]
  pot: number
  current: number | null
  finished: boolean
  showdown: boolean
  net: number[] | null
  winners: number[]
  last: LoggedAction
}

export interface HandView extends TableView {
  log: LoggedAction[]
}

export interface Legal {
  to_call: number
  can_check: boolean
  can_raise: boolean
  min_raise_to: number
  max_raise_to: number
}

export interface ReviewedDecision {
  index: number
  street: string
  board: string[]
  action: string
  amount_bb: number
  pot_bb: number
  to_call_bb: number
  equity: number
  opponents: number
  need: number | null
  loss_bb: number
  verdict: 'good' | 'leak' | 'mistake' | 'info'
  note: string
}

export interface PlayState {
  id: string
  /** Stacks carry over between hands instead of resetting to 100bb. */
  carry: boolean
  seats: PlayStyle[]
  hand: HandView
  /** Every table position since your last move, for step-by-step animation. */
  frames: TableView[]
  legal: Legal | null
  hands_played: number
  net_bb: number
  decisions: ReviewedDecision[]
  hand_id?: number
}

export interface Coach {
  /** What the opening chart does when you are first in ("Raise" or "Fold"), otherwise null. */
  chart: string | null
  to_call_bb: number
  pot_bb: number
  need: number | null
  equity: number
  opponents: number
}

export interface HandSummary {
  id: number
  created_at: string
  style: string
  net_bb: number
  worst_loss_bb: number
  hole: string[]
  board: string[]
  mistakes: number
}

export interface PlayStats {
  hands: number
  net_bb: number
  bb_per_100: number | null
  vpip: number | null
  pfr: number | null
  three_bet: number | null
  three_bet_chances: number
  cbet: number | null
  cbet_chances: number
  /** Went to showdown, as a share of flops seen. */
  wtsd: number | null
  flops_seen: number
  /** Won at showdown, as a share of showdowns. */
  wsd: number | null
  showdowns: number
  positions: PositionStats[]
  leaks: PlayLeak[]
}

export interface PositionStats {
  position: string
  hands: number
  net_bb: number
  vpip: number | null
  pfr: number | null
  /** Big blinds given up in reviewed decisions. */
  loss_bb: number
  mistakes: number
}

export interface PlayLeak {
  key: string
  title: string
  detail: string
  /** Where "practise this" leads: a page and its first parameter. */
  page: string
  arg: string
  label: string
}

export interface HandDetail extends HandSummary {
  record: {
    style: string
    seats: PlayStyle[]
    hand: HandView
    /** The table after every action, as you saw it, for the replayer. */
    frames?: TableView[]
    net_bb: number
    decisions: ReviewedDecision[]
  }
}

export interface ToyGame {
  key: string
  name: string
  blurb: string
  /** Card labels, weakest first. */
  cards: string[]
}

export interface ToyOutcome {
  role: 'bettor' | 'caller'
  card: string
  their_card: string
  their_action: string
  chips: number
}

export interface ToyResult extends ToyOutcome {
  action: string
  /** Average chips each of your options earns against this opponent. */
  values: Record<string, number>
  best: string
  active: string
  optimal: number
  lesson: string
}

export interface ToyFrequency {
  n: number
  yours: number | null
  optimal: number
  best: number
}

export interface ToyState {
  id: string
  game: ToyGame
  opponent: PlayStyle
  hand: { number: number; role: 'bettor' | 'caller'; card: string; actions: string[]; before: ToyOutcome[] }
  last: ToyResult | null
  hands_played: number
  summary: {
    chips: number
    expected: number
    best: number
    cards: { card: string; bet: ToyFrequency; call: ToyFrequency }[]
  }
}

export interface DrillStats {
  drill: string
  attempts: number
  correct: number
  accuracy: number
  mean_abs_error: number | null
  bias: number | null
  mean_ms: number | null
}

export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

/** One entry of a validation error: "to: Input should be less than 100". */
function problem(item: unknown): string {
  const { loc, msg } = item as { loc?: unknown[]; msg?: string }
  const field = Array.isArray(loc) ? loc.filter((part) => part !== 'body').join('.') : ''
  return [field, msg ?? 'invalid'].filter(Boolean).join(': ')
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...init?.headers },
  })
  if (!response.ok) {
    let detail = response.statusText || `HTTP ${response.status}`
    try {
      const body = (await response.json()) as { detail?: unknown }
      if (typeof body.detail === 'string') detail = body.detail
      else if (Array.isArray(body.detail)) detail = body.detail.map(problem).join('; ')
    } catch {
      // Body was not JSON; keep the status text.
    }
    throw new ApiError(response.status, detail)
  }
  try {
    return (await response.json()) as T
  } catch {
    throw new ApiError(response.status, 'Unexpected response from the server')
  }
}

export const api = {
  drills: () => request<DrillMeta[]>('/api/drills'),
  question: (key: string, seed?: number) =>
    request<Question>(`/api/drills/${encodeURIComponent(key)}/questions`, {
      method: 'POST',
      body: JSON.stringify(seed === undefined ? {} : { seed }),
    }),
  answer: (questionId: string, response: number | string | string[], elapsedMs?: number) =>
    request<GradeResult>('/api/answers', {
      method: 'POST',
      body: JSON.stringify({ question_id: questionId, response, elapsed_ms: elapsedMs }),
    }),
  stats: () => request<DrillStats[]>('/api/stats'),
  today: () => request<DailyPlan>('/api/today'),
  activity: () => request<Activity>('/api/activity'),
  curriculum: () => request<Curriculum>('/api/curriculum'),
  spots: () => request<Spot[]>('/api/preflop/spots'),
  paint: (spot: string, action: string, classes: string[]) =>
    request<PaintResult>('/api/preflop/paint', {
      method: 'POST',
      body: JSON.stringify({ spot, action, classes }),
    }),
  leaks: () => request<SpotLeak[]>('/api/preflop/leaks'),
  styles: () => request<PlayStyle[]>('/api/play/styles'),
  play: (carry = false) =>
    request<PlayState>('/api/play', { method: 'POST', body: JSON.stringify({ carry }) }),
  act: (id: string, kind: string, to?: number) =>
    request<PlayState>(`/api/play/${encodeURIComponent(id)}/act`, {
      method: 'POST',
      body: JSON.stringify(to === undefined ? { kind } : { kind, to }),
    }),
  nextHand: (id: string) => request<PlayState>(`/api/play/${encodeURIComponent(id)}/next`, { method: 'POST' }),
  coach: (id: string) => request<Coach>(`/api/play/${encodeURIComponent(id)}/coach`),
  hands: () => request<{ hands: HandSummary[]; stats: PlayStats }>('/api/hands'),
  hand: (id: number) => request<HandDetail>(`/api/hands/${id}`),
  toyMenu: () => request<{ games: ToyGame[]; opponents: PlayStyle[] }>('/api/toy'),
  toyStart: (game: string, opponent: string) =>
    request<ToyState>('/api/toy', { method: 'POST', body: JSON.stringify({ game, opponent }) }),
  toyAct: (id: string, action: string) =>
    request<ToyState>(`/api/toy/${encodeURIComponent(id)}/act`, { method: 'POST', body: JSON.stringify({ action }) }),
}

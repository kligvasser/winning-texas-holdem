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

export interface HandView {
  street: string
  button: number
  board: string[]
  hole: (string[] | null)[]
  behind: number[]
  bets: number[]
  pot: number
  current: number | null
  finished: boolean
  showdown: boolean
  net: number[] | null
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
  range_share: number
  need: number | null
  loss_bb: number
  verdict: 'good' | 'leak' | 'mistake' | 'info'
  note: string
}

export interface PlayState {
  id: string
  style: PlayStyle
  hand: HandView
  legal: Legal | null
  hands_played: number
  net_bb: number
  decisions: ReviewedDecision[]
  hand_id?: number
}

export interface Coach {
  to_call_bb: number
  pot_bb: number
  need: number | null
  equity: number
  range_share: number
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
}

export interface HandDetail extends HandSummary {
  record: { style: string; hand: HandView; net_bb: number; decisions: ReviewedDecision[] }
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

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...init?.headers },
  })
  if (!response.ok) {
    let detail = response.statusText
    try {
      const body = (await response.json()) as { detail?: unknown }
      if (typeof body.detail === 'string') detail = body.detail
    } catch {
      // Body was not JSON; keep the status text.
    }
    throw new ApiError(response.status, detail)
  }
  return (await response.json()) as T
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
  play: (style: string) =>
    request<PlayState>('/api/play', { method: 'POST', body: JSON.stringify({ style }) }),
  act: (id: string, kind: string, to?: number) =>
    request<PlayState>(`/api/play/${id}/act`, {
      method: 'POST',
      body: JSON.stringify(to === undefined ? { kind } : { kind, to }),
    }),
  nextHand: (id: string) => request<PlayState>(`/api/play/${id}/next`, { method: 'POST' }),
  coach: (id: string) => request<Coach>(`/api/play/${id}/coach`),
  hands: () => request<{ hands: HandSummary[]; stats: PlayStats }>('/api/hands'),
  hand: (id: number) => request<HandDetail>(`/api/hands/${id}`),
}

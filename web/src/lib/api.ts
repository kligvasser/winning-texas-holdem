export interface DrillMeta {
  key: string
  title: string
  concept: string
  tier: number
  description: string
}

export interface QuestionPayload {
  hole?: string[]
  villain?: string[]
  board?: string[]
  players?: string[][]
  pot?: number
  bet?: number
  [key: string]: unknown
}

export interface Question {
  id: string
  drill: string
  concept: string
  prompt: string
  kind: 'number' | 'choice'
  payload: QuestionPayload
  choices: string[]
  unit: string
}

export interface Review {
  rating: 'again' | 'hard' | 'good' | 'easy'
  due: string
}

export interface GradeResult {
  correct: boolean
  expected: number | string
  response: number | string
  error: number | null
  explanation: string[]
  highlight: string[]
  review?: Review | null
  reveal?: { grid?: string[][]; hand?: string; choices?: string[] }
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
  answer: (questionId: string, response: number | string, elapsedMs?: number) =>
    request<GradeResult>('/api/answers', {
      method: 'POST',
      body: JSON.stringify({ question_id: questionId, response, elapsed_ms: elapsedMs }),
    }),
  stats: () => request<DrillStats[]>('/api/stats'),
  today: () => request<DailyPlan>('/api/today'),
  curriculum: () => request<Curriculum>('/api/curriculum'),
  spots: () => request<Spot[]>('/api/preflop/spots'),
  paint: (spot: string, action: string, classes: string[]) =>
    request<PaintResult>('/api/preflop/paint', {
      method: 'POST',
      body: JSON.stringify({ spot, action, classes }),
    }),
  leaks: () => request<SpotLeak[]>('/api/preflop/leaks'),
}

export interface ResultRow {
  drill: string
  correct: boolean
  ms: number
}

export interface SessionProgress {
  position: number
  results: ResultRow[]
  skipped: number
}

/** A daily session saved in sessionStorage so a reload or navigation does not lose it. */
export interface SavedSession {
  day: string
  queue: string[]
  progress: SessionProgress
}

const KEY = 'holdem.today'

export function loadSession(day: string, storage: Storage = sessionStorage): SavedSession | null {
  try {
    const saved = JSON.parse(storage.getItem(KEY) ?? 'null') as SavedSession | null
    return saved && saved.day === day ? saved : null
  } catch {
    return null
  }
}

export function saveSession(session: SavedSession | null, storage: Storage = sessionStorage): void {
  try {
    if (session) storage.setItem(KEY, JSON.stringify(session))
    else storage.removeItem(KEY)
  } catch {
    // Storage can be unavailable (private mode); the session just will not resume.
  }
}

/** Personal bests for speed rounds, kept in this browser only. */

const PREFIX = 'holdem.speed.'

export function loadBest(key: string, storage: Storage = localStorage): number {
  try {
    return Number(storage.getItem(PREFIX + key)) || 0
  } catch {
    return 0
  }
}

export function saveBest(key: string, score: number, storage: Storage = localStorage): boolean {
  const best = loadBest(key, storage)
  if (score <= best) return false
  try {
    storage.setItem(PREFIX + key, String(score))
  } catch {
    // Storage unavailable: the best score just will not stick.
  }
  return true
}

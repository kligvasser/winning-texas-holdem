import { afterEach, describe, expect, it, vi } from 'vitest'
import { ApiError, api } from './api'

function mockFetch(body: unknown, init: { ok?: boolean; status?: number; statusText?: string; json?: boolean } = {}) {
  const response = {
    ok: init.ok ?? true,
    status: init.status ?? 200,
    statusText: init.statusText ?? 'OK',
    json: init.json === false ? () => Promise.reject(new Error('not json')) : () => Promise.resolve(body),
  }
  const fn = vi.fn().mockResolvedValue(response)
  vi.stubGlobal('fetch', fn)
  return fn
}

afterEach(() => vi.unstubAllGlobals())

describe('api', () => {
  it('lists drills and stats', async () => {
    const fetch = mockFetch([{ key: 'x' }])
    expect(await api.drills()).toEqual([{ key: 'x' }])
    expect(fetch).toHaveBeenCalledWith('/api/drills', expect.objectContaining({ headers: { 'Content-Type': 'application/json' } }))
    await api.stats()
    expect(fetch).toHaveBeenLastCalledWith('/api/stats', expect.anything())
  })

  it('fetches the daily plan and curriculum', async () => {
    const fetch = mockFetch({})
    await api.today()
    expect(fetch).toHaveBeenLastCalledWith('/api/today', expect.anything())
    await api.curriculum()
    expect(fetch).toHaveBeenLastCalledWith('/api/curriculum', expect.anything())
    await api.activity()
    expect(fetch).toHaveBeenLastCalledWith('/api/activity', expect.anything())
  })

  it('calls the preflop endpoints', async () => {
    const fetch = mockFetch([])
    await api.spots()
    expect(fetch).toHaveBeenLastCalledWith('/api/preflop/spots', expect.anything())
    await api.leaks()
    expect(fetch).toHaveBeenLastCalledWith('/api/preflop/leaks', expect.anything())
    await api.paint('utg-open', 'Raise', ['AA'])
    expect(fetch).toHaveBeenLastCalledWith(
      '/api/preflop/paint',
      expect.objectContaining({ method: 'POST', body: '{"spot":"utg-open","action":"Raise","classes":["AA"]}' }),
    )
  })

  it('asks for a question with and without a seed', async () => {
    const fetch = mockFetch({ id: 'q' })
    await api.question('pot odds', 3)
    expect(fetch).toHaveBeenLastCalledWith('/api/drills/pot%20odds/questions', expect.objectContaining({ method: 'POST', body: '{"seed":3}' }))
    await api.question('outs')
    expect(fetch).toHaveBeenLastCalledWith('/api/drills/outs/questions', expect.objectContaining({ body: '{}' }))
  })

  it('posts answers', async () => {
    const fetch = mockFetch({ correct: true })
    await api.answer('q1', 25, 1200)
    expect(fetch).toHaveBeenLastCalledWith('/api/answers', expect.objectContaining({ body: '{"question_id":"q1","response":25,"elapsed_ms":1200}' }))
  })

  it('raises ApiError with the server detail', async () => {
    mockFetch({ detail: 'question not found' }, { ok: false, status: 404, statusText: 'Not Found' })
    await expect(api.drills()).rejects.toEqual(new ApiError(404, 'question not found'))
  })

  it('falls back to the status text', async () => {
    mockFetch({ detail: [{ msg: 'bad' }] }, { ok: false, status: 422, statusText: 'Unprocessable' })
    await expect(api.drills()).rejects.toMatchObject({ status: 422, message: 'Unprocessable', name: 'ApiError' })
    mockFetch(null, { ok: false, status: 500, statusText: 'Server Error', json: false })
    await expect(api.drills()).rejects.toMatchObject({ status: 500, message: 'Server Error' })
  })
})

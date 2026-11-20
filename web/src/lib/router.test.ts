import { describe, expect, it } from 'vitest'
import { href, parseHash, router } from './router.svelte'

describe('router', () => {
  it('parses hashes', () => {
    expect(parseHash('')).toEqual({ page: 'home', params: [] })
    expect(parseHash('#/')).toEqual({ page: 'home', params: [] })
    expect(parseHash('#/%')).toEqual({ page: 'home', params: [] })
    expect(parseHash('#/play/%E0%A4%A')).toEqual({ page: 'home', params: [] })
    expect(parseHash('#/math-lab/outs')).toEqual({ page: 'math-lab', params: ['outs'] })
    expect(parseHash('#math-lab/a%20b')).toEqual({ page: 'math-lab', params: ['a b'] })
  })

  it('builds hrefs', () => {
    expect(href('math-lab', 'a b')).toBe('#/math-lab/a%20b')
  })

  it('follows hash changes', async () => {
    router.go('stats')
    window.dispatchEvent(new HashChangeEvent('hashchange'))
    expect(router.route).toEqual({ page: 'stats', params: [] })
  })

  it('starts each page at the top with focus in its content', () => {
    const main = document.createElement('main')
    main.tabIndex = -1
    document.body.append(main)
    router.go('learn')
    window.dispatchEvent(new HashChangeEvent('hashchange'))
    expect(window.scrollTo).toHaveBeenLastCalledWith(0, 0)
    expect(main).toHaveFocus()
    main.remove()
    window.dispatchEvent(new HashChangeEvent('hashchange')) // no <main>: nothing to focus, no error
  })
})

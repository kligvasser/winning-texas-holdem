/** A tiny hash router: "#/math-lab/outs" -> { page: "math-lab", params: ["outs"] }. */

export interface Route {
  page: string
  params: string[]
}

export function parseHash(hash: string): Route {
  let parts: string[]
  try {
    parts = hash.replace(/^#\/?/, '').split('/').filter(Boolean).map(decodeURIComponent)
  } catch {
    parts = [] // a malformed escape such as "#/%" goes home instead of crashing the app
  }
  return { page: parts[0] ?? 'home', params: parts.slice(1) }
}

export function href(page: string, ...params: string[]): string {
  return '#/' + [page, ...params].map(encodeURIComponent).join('/')
}

class Router {
  route = $state<Route>(parseHash(window.location.hash))

  constructor() {
    window.addEventListener('hashchange', () => {
      this.route = parseHash(window.location.hash)
      // A new page starts at its top, and keyboard and screen-reader users start in its content.
      window.scrollTo(0, 0)
      document.querySelector('main')?.focus({ preventScroll: true })
    })
  }

  go(page: string, ...params: string[]): void {
    window.location.hash = href(page, ...params)
  }
}

export const router = new Router()

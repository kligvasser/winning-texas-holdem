/** A tiny hash router: "#/math-lab/outs" -> { page: "math-lab", params: ["outs"] }. */

export interface Route {
  page: string
  params: string[]
}

export function parseHash(hash: string): Route {
  const parts = hash.replace(/^#\/?/, '').split('/').filter(Boolean).map(decodeURIComponent)
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
    })
  }

  go(page: string, ...params: string[]): void {
    window.location.hash = href(page, ...params)
  }
}

export const router = new Router()

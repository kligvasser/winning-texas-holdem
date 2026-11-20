import '@testing-library/jest-dom/vitest'
import { vi } from 'vitest'

// jsdom has no scrolling; the router scrolls to the top on every page change.
window.scrollTo = vi.fn()

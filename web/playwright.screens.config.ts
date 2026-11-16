import { defineConfig } from '@playwright/test'
import base from './playwright.config'

// Regenerates the README screenshots: `npm run screenshots`.
export default defineConfig({
  ...base,
  testDir: './screenshots',
  projects: [{ name: 'screens', use: { viewport: { width: 1280, height: 820 } } }],
  webServer: {
    ...base.webServer,
    // Same server, but with a seeded ten-day practice history so progress pages have content.
    command:
      'npm run build && cd .. && uv run python scripts/seed_demo.py data/screens && ' +
      'HOLDEM_DATA_DIR=data/screens uv run python -m holdem --port 8765',
  },
})

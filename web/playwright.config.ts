import { defineConfig, devices } from '@playwright/test'

const PORT = 8765

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  reporter: 'list',
  use: { baseURL: `http://127.0.0.1:${PORT}`, trace: 'retain-on-failure' },
  projects: [
    { name: 'desktop', use: { ...devices['Desktop Chrome'] } },
    { name: 'phone', use: { ...devices['Pixel 7'] } },
  ],
  webServer: {
    // Serves the built front end from the real Python backend with a throwaway database.
    command: `npm run build && cd .. && rm -rf data/e2e && HOLDEM_DATA_DIR=data/e2e uv run python -m holdem --port ${PORT}`,
    url: `http://127.0.0.1:${PORT}/api/health`,
    reuseExistingServer: false,
    timeout: 120_000,
  },
})

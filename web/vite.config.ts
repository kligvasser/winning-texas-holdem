/// <reference types="vitest/config" />
import { svelte } from '@sveltejs/vite-plugin-svelte'
import { svelteTesting } from '@testing-library/svelte/vite'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [svelte(), svelteTesting()],
  server: {
    proxy: { '/api': 'http://127.0.0.1:8000' },
  },
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    include: ['src/**/*.test.ts'],
    coverage: {
      provider: 'v8',
      include: ['src/**/*.{ts,svelte}'],
      exclude: ['src/main.ts', 'src/test/**', 'src/**/*.test.ts', 'src/**/*.d.ts'],
      thresholds: {
        'src/**/*.ts': { lines: 100, functions: 100, branches: 100, statements: 100 },
        // The Svelte compiler wraps each template interpolation in `?? ""`, and v8 counts
        // every one as a branch even when the value can never be nullish. Lines,
        // statements and functions stay at 100%; branches are gated slightly lower.
        'src/**/*.svelte': { lines: 100, functions: 100, branches: 85, statements: 100 },
      },
    },
  },
})

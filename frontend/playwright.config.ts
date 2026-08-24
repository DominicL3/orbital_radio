import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './e2e',
  use: { ...devices['Desktop Chrome'], baseURL: 'http://127.0.0.1:4174' },
  webServer: { command: 'npm run dev -- --host 127.0.0.1 --port 4174', port: 4174, reuseExistingServer: true },
})

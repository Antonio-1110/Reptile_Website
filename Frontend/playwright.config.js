import { defineConfig, devices } from '@playwright/test';

// `npm run e2e`: starts a throwaway backend (e2e/start-backend.sh, port 8001) and the Vite dev server
// pointed at it (port 5174), then drives Chromium through real user flows.
export default defineConfig({
  testDir: './e2e',
  fullyParallel: false, // the flows share one database
  workers: 1,
  retries: 0,
  reporter: process.env.CI ? [['list'], ['html', { open: 'never' }]] : 'list',
  use: {
    baseURL: 'http://127.0.0.1:5174',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: [
    {
      command: './e2e/start-backend.sh',
      url: 'http://127.0.0.1:8001/api/posts/species/',
      timeout: 120_000,
      reuseExistingServer: false,
    },
    {
      command: 'npm run dev -- --host 127.0.0.1 --port 5174 --strictPort',
      url: 'http://127.0.0.1:5174',
      env: { VITE_API_URL: 'http://127.0.0.1:8001/api' },
      timeout: 60_000,
      reuseExistingServer: false,
    },
  ],
});

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
  projects: [{
    name: 'chromium',
    use: {
      ...devices['Desktop Chrome'],
      // Google's sign-in script is never fetched for real: tests that need the button stand in for
      // it (sign-in-layout.spec.js), and the rest see the "couldn't load" message every time.
      launchOptions: { args: ['--host-resolver-rules=MAP accounts.google.com ~NOTFOUND'] },
    },
  }],
  webServer: [
    {
      command: './e2e/start-backend.sh',
      url: 'http://127.0.0.1:8001/api/v1/posts/species/',
      timeout: 120_000,
      reuseExistingServer: false,
    },
    {
      command: 'npm run dev -- --host 127.0.0.1 --port 5174 --strictPort',
      url: 'http://127.0.0.1:5174',
      // A made-up Google client ID, so the sign-in page draws its Google button (sign-in-layout.spec.js).
      env: { VITE_API_URL: 'http://127.0.0.1:8001/api', VITE_GOOGLE_CLIENT_ID: 'e2e.apps.googleusercontent.com' },
      timeout: 60_000,
      reuseExistingServer: false,
    },
  ],
});

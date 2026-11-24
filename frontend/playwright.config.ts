import { defineConfig, devices } from '@playwright/test';

// Default target: the docker-compose.test.yml stack managed by global-setup
// (E2E_PORT moves it off :8001). Set PW_BASE_URL to test any already-running
// stack instead.
const baseURL = process.env.PW_BASE_URL ?? `http://localhost:${process.env.E2E_PORT ?? '8001'}`;

export default defineConfig({
  testDir: './e2e',
  globalSetup: './e2e/global-setup.ts',
  globalTeardown: './e2e/global-teardown.ts',
  retries: process.env.CI ? 2 : 0,
  timeout: 45_000,
  // Specs reset shared database state; one worker keeps them deterministic.
  workers: 1,
  reporter: process.env.CI ? 'github' : 'list',
  use: {
    baseURL,
    trace: 'on-first-retry',
    // The animation code already guards on prefers-reduced-motion; skipping
    // the explosion/pulse effects removes a whole class of flake.
    contextOptions: { reducedMotion: 'reduce' },
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
    { name: 'firefox', use: { ...devices['Desktop Firefox'] } },
    { name: 'webkit', use: { ...devices['Desktop Safari'] } },
  ],
});

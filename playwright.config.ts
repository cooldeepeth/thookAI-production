import { defineConfig, devices } from "@playwright/test";

/**
 * ThookAI E2E Playwright configuration.
 *
 * Dual webServer setup:
 *   - FastAPI backend on port 8001
 *   - CRA React frontend on port 3000
 *
 * Tests live in ./e2e/
 *
 * The `wedge` project targets the three critical-path specs in e2e/wedge/.
 * It uses REACT_APP_API_URL (or WEDGE_BASE_URL) so CI can aim at staging
 * while local runs fall back to the webServer-started localhost stack.
 */
const WEDGE_BASE_URL =
  process.env.WEDGE_BASE_URL ||
  process.env.REACT_APP_API_URL ||
  "http://localhost:8001";

export default defineConfig({
  testDir: "./e2e",
  /* 60 seconds per test — content generation can be slow */
  timeout: 60000,
  /* Retry on CI to handle transient flakiness */
  retries: process.env.CI ? 2 : 0,
  /* Serial in CI for stability; parallel locally */
  workers: process.env.CI ? 1 : undefined,

  use: {
    baseURL: "http://localhost:3000",
    /* Collect trace on first retry for debugging */
    trace: "on-first-retry",
    /* Screenshot only when a test fails */
    screenshot: "only-on-failure",
  },

  projects: [
    {
      name: "chromium",
      testIgnore: ["**/wedge/**"],
      use: { ...devices["Desktop Chrome"] },
    },
    {
      name: "firefox",
      testIgnore: ["**/wedge/**"],
      use: { ...devices["Desktop Firefox"] },
    },
    {
      name: "webkit",
      testIgnore: ["**/wedge/**"],
      use: { ...devices["Desktop Safari"] },
    },
    {
      name: "mobile-chrome",
      testIgnore: ["**/wedge/**"],
      use: { ...devices["Pixel 5"] },
    },
    {
      name: "mobile-safari",
      testIgnore: ["**/wedge/**"],
      use: { ...devices["iPhone 13 Pro"] },
    },
    {
      name: "wedge",
      testMatch: ["**/wedge/**/*.spec.ts"],
      /* 90s per test — persona extraction polls up to 60s */
      timeout: 90_000,
      use: {
        ...devices["Desktop Chrome"],
        baseURL: WEDGE_BASE_URL,
      },
    },
  ],

  reporter: [["html", { open: "never" }], ["list"]],

  /* Start both servers before running tests */
  webServer: [
    {
      /* FastAPI backend */
      command: "cd backend && uvicorn server:app --host 0.0.0.0 --port 8001",
      url: "http://localhost:8001/health",
      reuseExistingServer: !process.env.CI,
      timeout: 120000,
    },
    {
      /* CRA React frontend */
      command: "cd frontend && npm start",
      url: "http://localhost:3000",
      reuseExistingServer: !process.env.CI,
      timeout: 120000,
      env: {
        BROWSER: "none",
        PORT: "3000",
        REACT_APP_API_URL: "http://localhost:8001/api",
      },
    },
  ],
});

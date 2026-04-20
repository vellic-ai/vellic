import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  outputDir: "./playwright-results",
  timeout: 30_000,
  fullyParallel: false,
  forbidOnly: !!process.env["CI"],
  retries: process.env["CI"] ? 1 : 0,
  workers: 1,
  reporter: process.env["CI"]
    ? [
        ["github"],
        ["html", { outputFolder: "playwright-report", open: "never" }],
      ]
    : [["list"], ["html", { outputFolder: "playwright-report", open: "never" }]],
  use: {
    baseURL: process.env["E2E_BASE_URL"] ?? "http://localhost:5173",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
    trace: "retain-on-failure",
  },
  projects: [
    {
      name: "setup",
      testMatch: /global\.setup\.ts/,
    },
    {
      name: "chromium",
      use: {
        ...devices["Desktop Chrome"],
        storageState: "playwright/.auth/state.json",
      },
      dependencies: ["setup"],
      testIgnore: /global\.setup\.ts/,
    },
  ],
  webServer: {
    command: "npm run dev",
    url: process.env["E2E_BASE_URL"] ?? "http://localhost:5173",
    reuseExistingServer: !process.env["CI"],
  },
});

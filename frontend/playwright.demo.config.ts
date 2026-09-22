import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  testMatch: "ask-workspace.spec.ts",
  fullyParallel: false,
  retries: 0,
  reporter: "line",
  outputDir: "./test-results/demo-recording",
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL ?? "http://frontend:3000",
    video: "on",
    trace: "off",
    screenshot: "off",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});

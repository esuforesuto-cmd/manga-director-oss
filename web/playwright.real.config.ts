import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e-real",
  timeout: 120_000,
  expect: { timeout: 15_000 },
  workers: 1,
  use: {
    baseURL: "http://127.0.0.1:3000",
    trace: "retain-on-failure"
  },
  webServer: [
    {
      command: "node --experimental-strip-types e2e-real/real-api.ts",
      url: "http://127.0.0.1:8000/health",
      reuseExistingServer: false,
      timeout: 120_000
    },
    {
      command: "npm run dev -- --hostname 127.0.0.1 --port 3000",
      url: "http://127.0.0.1:3000",
      env: { NEXT_PUBLIC_MANGA_DIRECTOR_API_URL: "http://127.0.0.1:8000" },
      reuseExistingServer: false,
      timeout: 120_000
    }
  ]
});

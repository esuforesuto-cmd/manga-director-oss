import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  timeout: 30_000,
  use: { baseURL: "http://127.0.0.1:3000" },
  webServer: [
    { command: "node e2e/mock-api.mjs", port: 4010, reuseExistingServer: false },
    { command: "node e2e/start-ui.mjs", port: 3000, reuseExistingServer: false }
  ]
});

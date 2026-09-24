import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./e2e",
  workers:1,
  use: { baseURL: "http://127.0.0.1:18081", headless: true },
  webServer: {
    command: "npm run build && python ../backend/e2e_server.py",
    url: "http://127.0.0.1:18081/api/health/",
    reuseExistingServer: false,
  },
});

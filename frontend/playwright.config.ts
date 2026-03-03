import { defineConfig } from "@playwright/test";
import { existsSync } from "node:fs";

const useExistingServers = process.env.PLAYWRIGHT_USE_EXISTING === "true";
const inferredDockerMode = !existsSync("../backend");
const dockerMode = process.env.PLAYWRIGHT_DOCKER_MODE === "true" || inferredDockerMode;
const dockerFrontendPort = process.env.PLAYWRIGHT_FRONTEND_PORT || "3100";
const dockerFrontendUrl = `http://localhost:${dockerFrontendPort}`;

export default defineConfig({
  testDir: "./tests/e2e",
  timeout: 120000,
  use: {
    baseURL: process.env.E2E_BASE_URL || (dockerMode ? dockerFrontendUrl : "http://localhost:3000")
  },
  webServer: useExistingServers
    ? undefined
    : dockerMode
      ? [
          {
            command: `NEXT_PUBLIC_API_URL=http://backend:8000 npm run dev -- --hostname 0.0.0.0 --port ${dockerFrontendPort}`,
            url: dockerFrontendUrl,
            reuseExistingServer: false,
            timeout: 120000
          }
        ]
      : [
        {
          command:
            "cd ../backend && PYTHONPATH=. USE_SQLITE=true LOCAL_DATABASE_URL=sqlite+pysqlite:///./playwright.db alembic upgrade head && PYTHONPATH=. USE_SQLITE=true LOCAL_DATABASE_URL=sqlite+pysqlite:///./playwright.db python3 -m app.utils.seed_demo && PYTHONPATH=. USE_SQLITE=true LOCAL_DATABASE_URL=sqlite+pysqlite:///./playwright.db FRONTEND_ORIGIN=http://localhost:3000 uvicorn app.main:app --host 127.0.0.1 --port 8000",
          url: "http://localhost:8000/health",
          reuseExistingServer: false,
          timeout: 120000
        },
        {
          command: "NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev -- --hostname localhost --port 3000",
          url: "http://localhost:3000",
          reuseExistingServer: false,
          timeout: 120000
        }
      ]
});

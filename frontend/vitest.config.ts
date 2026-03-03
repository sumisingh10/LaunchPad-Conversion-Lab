import { defineConfig } from "vitest/config";
import path from "path";

export default defineConfig({
  resolve: {
    alias: {
      "@": path.resolve(__dirname, ".")
    }
  },
  esbuild: {
    jsx: "automatic"
  },
  test: {
    include: ["tests/unit/**/*.test.ts?(x)"],
    exclude: ["tests/e2e/**", "node_modules/**"],
    environment: "jsdom",
    setupFiles: ["./vitest.setup.ts"],
    globals: true,
    pool: "forks",
    poolOptions: {
      forks: {
        minForks: 1,
        maxForks: 1
      }
    }
  }
});

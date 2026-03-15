import path from "node:path";

import { defineConfig } from "vitest/config";

export default defineConfig({
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "."),
    },
  },
  test: {
    environment: "jsdom",
    exclude: ["e2e/**", "node_modules/**"],
    globals: true,
    setupFiles: ["./test/setup.ts"],
    coverage: {
      provider: "v8",
      include: ["components/**", "lib/**", "app/**"],
      exclude: ["**/*.test.*", "**/*.spec.*", "e2e/**"],
      thresholds: {
        lines: 60,
        branches: 50,
        functions: 50,
        statements: 60,
      },
    },
  },
});

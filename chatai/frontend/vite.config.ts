import { defineConfig } from "vite";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";

const rootDir = fileURLToPath(new URL(".", import.meta.url));
import react from "@vitejs/plugin-react";
import { configDefaults } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true
      }
    }
  },
  build: {
    rollupOptions: {
      input: {
        main: resolve(rootDir, "index.html"),
        control: resolve(rootDir, "control-center.html")
      }
    }
  },
  test: {
    globals: true,
    environment: "happy-dom",
    setupFiles: "./src/setupTests.ts",
    coverage: {
      provider: "istanbul",
      reporter: ["text", "lcov"],
      exclude: [...configDefaults.coverage.exclude, "src/main.tsx", "src/main.js", "src/App.tsx"],
    }
  }
});

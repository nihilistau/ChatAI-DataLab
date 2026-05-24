var __spreadArray = (this && this.__spreadArray) || function (to, from, pack) {
    if (pack || arguments.length === 2) for (var i = 0, l = from.length, ar; i < l; i++) {
        if (ar || !(i in from)) {
            if (!ar) ar = Array.prototype.slice.call(from, 0, i);
            ar[i] = from[i];
        }
    }
    return to.concat(ar || Array.prototype.slice.call(from));
};
import { defineConfig } from "vite";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";
var rootDir = fileURLToPath(new URL(".", import.meta.url));
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
            exclude: __spreadArray(__spreadArray([], configDefaults.coverage.exclude, true), ["src/main.tsx", "src/main.js", "src/App.tsx"], false),
        }
    }
});

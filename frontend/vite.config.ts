import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import path from "node:path";
import { readFileSync } from "node:fs";

const { version } = JSON.parse(readFileSync("./package.json", "utf-8")) as { version: string };

export default defineConfig({
  define: {
    __APP_VERSION__: JSON.stringify(version),
  },
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  build: {
    outDir: "dist",
    emptyOutDir: true,
  },
  server: {
    port: 5173,
    proxy: {
      "/admin": {
        target: "http://localhost:8001",
        changeOrigin: true,
      },
      "/health": {
        target: "http://localhost:8001",
        changeOrigin: true,
      },
    },
  },
  preview: {
    port: 5173,
    proxy: {
      "/admin": {
        target: "http://localhost:8001",
        changeOrigin: true,
      },
      "/health": {
        target: "http://localhost:8001",
        changeOrigin: true,
      },
    },
  },
  test: {
    globals: true,
    environment: "jsdom",
    environmentOptions: {
      jsdom: { url: "http://localhost:5173" },
    },
    setupFiles: ["./src/test/setup.ts"],
    css: true,
    include: ["src/**/*.{test,spec}.{ts,tsx}"],
    env: {
      NODE_ENV: "development",
    },
  },
});

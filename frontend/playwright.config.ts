import { defineConfig } from "@playwright/test";

/**
 * Campus-AI frontend smoke test config.
 *
 * Kis site ke against chalega:
 *   FRONTEND_URL  (default = Vercel prod)
 *   API_URL       (default = Render backend, login token ke liye)
 *
 * Windows PowerShell me override:
 *   $env:FRONTEND_URL="http://localhost:3000"; $env:API_URL="http://127.0.0.1:8000"
 */
export default defineConfig({
  testDir: "./e2e",
  // Ek role test me 16 tak pages khulte hain + pehla role Vercel/Render cold
  // start jhelata hai, isliye budget bada rakha hai.
  timeout: 180_000,
  expect: { timeout: 15_000 },
  retries: 0,
  workers: 1,
  reporter: [["list"]],
  use: {
    baseURL: process.env.FRONTEND_URL || "https://campus-ai-eta.vercel.app",
    headless: true,
    ignoreHTTPSErrors: true,
    actionTimeout: 15_000,
    navigationTimeout: 45_000,
  },
});

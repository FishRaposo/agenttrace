import { defineConfig } from "@playwright/test";
import base from "./playwright.config";
export default defineConfig({
  ...base,
  testMatch: "**/connected*.spec.ts",
  testIgnore: [],
  timeout: 180000,
});

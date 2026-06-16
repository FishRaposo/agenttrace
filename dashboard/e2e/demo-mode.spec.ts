import { test, expect } from "@playwright/test";

/**
 * Demo-mode smoke spec.
 *
 * With no AgentTrace backend running, the API client falls back to in-memory
 * fixtures and surfaces a visible "Demo mode" banner. These checks confirm the
 * dashboard renders meaningful content offline rather than an error screen.
 *
 * The Playwright webServer runs `next dev` without a backend, so demo mode is
 * exercised naturally. We additionally block backend calls to guarantee the
 * offline path is hit deterministically.
 */
test.describe("AgentTrace demo mode (offline)", () => {
  test.beforeEach(async ({ page }) => {
    // Force every backend request to fail so the demo fallback always engages.
    await page.route("**/localhost:8000/**", (route) => route.abort());
    await page.route("**/api/**", (route) => route.abort());
  });

  test("dashboard shows the demo banner and sample stats", async ({ page }) => {
    await page.goto("http://localhost:3000");
    await expect(page.getByTestId("demo-mode-banner")).toBeVisible({
      timeout: 10000,
    });
    await expect(page.locator("text=Total Runs")).toBeVisible();
    // Sample data should populate the recent-runs table with a known demo run.
    await expect(page.locator("text=research-agent")).toBeVisible();
  });

  test("runs page is explorable with sample data", async ({ page }) => {
    await page.goto("http://localhost:3000/runs");
    await expect(page.getByTestId("demo-mode-banner")).toBeVisible({
      timeout: 10000,
    });
    await expect(page.locator("h2")).toContainText("Runs");
  });

  test("costs page renders analytics from demo fixtures", async ({ page }) => {
    await page.goto("http://localhost:3000/costs");
    await expect(page.getByTestId("demo-mode-banner")).toBeVisible({
      timeout: 10000,
    });
    await expect(page.locator("h2")).toContainText("Cost Analytics");
  });
});

import { test, expect } from "@playwright/test";

test.describe("AgentTrace Dashboard E2E Tests", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
  });

  test("homepage loads and displays stats", async ({ page }) => {
    await expect(page.getByRole("heading", { name: "AgentTrace", exact: true })).toBeVisible();
    await expect(page.locator("text=Agent Observability")).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "Operation Volume Trajectory" })
    ).toBeVisible();
    await expect(page.locator("text=Total Runs")).toBeVisible();
  });

  test("navigation to runs page", async ({ page }) => {
    await page.click("text=Runs");
    await expect(page).toHaveURL(/\/runs/);
    await expect(page.locator("h2")).toContainText("Runs");
  });

  test("dark mode toggle", async ({ page }) => {
    const toggleButton = page.locator('button[aria-label="Toggle theme"]');
    await toggleButton.click();
    await expect(page.locator("html")).toHaveClass(/dark/);
    await toggleButton.click();
    await expect(page.locator("html")).not.toHaveClass(/dark/);
  });

  test("status filtering on runs page", async ({ page }) => {
    await page.click("text=Runs");
    await page.click('button:has-text("completed")');
    await expect(page.locator('button:has-text("completed")')).toHaveClass(/bg-trace-600/);
  });

  test("search functionality on runs page", async ({ page }) => {
    await page.click("text=Runs");
    await page.fill('input[placeholder="Search runs..."]', "test");
    // Verify search input has value
    const searchInput = page.locator('input[placeholder="Search runs..."]');
    await expect(searchInput).toHaveValue("test");
  });

  test("pagination controls on runs page", async ({ page }) => {
    await page.click("text=Runs");
    const paginationSummary = page.locator("text=/Showing .* of /");
    if (await paginationSummary.isVisible()) {
      await expect(page.locator('button:has-text("Previous")')).toBeVisible();
      await expect(page.locator('button:has-text("Next")')).toBeVisible();
    } else {
      await expect(page.locator('button:has-text("Previous")')).toHaveCount(0);
      await expect(page.locator('button:has-text("Next")')).toHaveCount(0);
    }
  });

  test("costs page loads with analytics", async ({ page }) => {
    await page.click("text=Costs");
    await expect(page).toHaveURL(/\/costs/);
    await expect(page.locator("h2")).toContainText("Cost & FinOps");
    // Budget bars or charts should be present
    const chart = page.locator("[data-testid='cost-chart'], canvas, svg").first();
    await expect(chart).toBeVisible({ timeout: 5000 });
  });

  test("live tail page loads and connects", async ({ page }) => {
    await page.click("text=Live");
    await expect(page).toHaveURL(/\/live/);
    await expect(page.locator("h2")).toContainText("Live Tail");
    await expect(page.locator("text=Waiting for spans..."))
      .toBeVisible({ timeout: 5000 });
  });

  test("run detail page shows timeline and diff", async ({ page }) => {
    // Navigate to runs and click first run if available
    await page.click("text=Runs");
    const firstRun = page.locator("[data-testid='run-row']").first();
    if (await firstRun.isVisible()) {
      await firstRun.click();
      await expect(page).toHaveURL(/\/runs\//);
      // Timeline should be visible
      await expect(page.locator("text=Timeline")).toBeVisible();
      // Diff tab should be present
      await page.click("text=Diff");
      await expect(page.locator("text=Select runs to compare")).toBeVisible();
    }
  });
});

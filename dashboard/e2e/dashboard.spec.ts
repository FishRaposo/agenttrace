import { test, expect } from "@playwright/test";

test.describe("AgentTrace Dashboard E2E Tests", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("http://localhost:3000");
  });

  test("homepage loads and displays stats", async ({ page }) => {
    await expect(page.locator("h1")).toContainText("AgentTrace");
    await expect(page.locator("text=Agent Observability")).toBeVisible();
    await expect(page.locator("h2")).toContainText("Dashboard");
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
});

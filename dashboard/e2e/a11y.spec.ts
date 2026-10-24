import { test, expect } from "@playwright/test";
import { AxeBuilder } from "@axe-core/playwright";

const routes = [
  ["investigation", "/"],
  ["runs", "/runs"],
  ["costs", "/costs"],
  ["live", "/live"],
  ["workflow", "/workflow"],
] as const;

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() =>
    localStorage.setItem(
      "agenttrace.preferences.v1",
      JSON.stringify({ source: "sample" }),
    ),
  );
});

for (const [name, path] of routes) {
  test(`axe wcag2a/aa: ${name}`, async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto(path);
    await expect(page.locator("main")).toBeVisible();
    const results = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
      .analyze();
    expect(results.violations).toEqual([]);
  });
}

test("axe wcag2a/aa: run detail", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/runs");
  await page.getByRole("link", { name: /request-/ }).first().click();
  await expect(page.locator("main")).toBeVisible();
  const results = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
    .analyze();
  expect(results.violations).toEqual([]);
});

for (const [name, path] of routes.slice(0, 2)) {
  test(`axe wcag2a/aa at 390px: ${name}`, async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto(path);
    await expect(page.locator("main")).toBeVisible();
    const results = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
      .analyze();
    expect(results.violations).toEqual([]);
  });
}

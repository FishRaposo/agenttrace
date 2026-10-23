import { test, expect } from "@playwright/test";
import path from "node:path";
const sizes = [
  { width: 390, height: 844 },
  { width: 768, height: 1024 },
  { width: 1440, height: 900 },
];
for (const size of sizes) {
  test(`offline investigation ${size.width}x${size.height}`, async ({
    page,
    baseURL,
  }) => {
    await page.setViewportSize(size);
    await page.emulateMedia({ reducedMotion: "reduce" });
    const external: string[] = [];
    const errors: string[] = [];
    page.on("request", (request) => {
      if (new URL(request.url()).origin !== new URL(baseURL!).origin)
        external.push(request.url());
    });
    page.on("pageerror", (error) => errors.push(error.message));
    page.on("console", (message) => {
      if (message.type() === "error") errors.push(message.text());
    });
    await page.addInitScript(() =>
      localStorage.setItem(
        "agenttrace.preferences.v1",
        JSON.stringify({ source: "sample" }),
      ),
    );
    await page.goto("/");
    await expect(page).toHaveTitle(/AgentTrace/);
    await expect(
      page.getByRole("heading", {
        name: "Find the failing step in an AI workflow, even when requests overlap.",
      }),
    ).toBeVisible();
    await expect(page.getByTestId("run-count")).toHaveText("20");
    await expect(page.getByTestId("completed-count")).toHaveText("17");
    await page
      .getByRole("button", { name: "Investigate a failure", exact: true })
      .click();
    await expect(
      page.getByRole("region", { name: "Guided investigation" }),
    ).toBeVisible();
    await expect(page.getByTestId("run-count")).toHaveText("20");
    const guided = page.getByRole("region", { name: "Guided investigation" });
    await guided
      .getByRole("button", { name: "Next step", exact: true })
      .click();
    await expect(
      page.getByRole("heading", { name: "Request timeline" }),
    ).toBeVisible();
    await page
      .getByRole("list", { name: "Ordered text stages" })
      .getByRole("button", { name: /retrieval/ })
      .click();
    await expect(
      page.getByRole("region", { name: "Selected span" }),
    ).toContainText("Retrieval returned no matching source");
    await page.screenshot({
      path: path.resolve(
        process.env.AGENTTRACE_SCREENSHOTS ??
          "../../../.tmp/agenttrace-20261023/screenshots",
        `sample-failure-${size.width}.png`,
      ),
      fullPage: true,
    });
    await guided
      .getByRole("button", { name: "Next step", exact: true })
      .click();
    await page
      .getByRole("button", { name: "Compare repair", exact: true })
      .click();
    await expect(
      page.getByRole("heading", { name: "Run comparison" }),
    ).toBeVisible();
    await page.screenshot({
      path: path.resolve(
        process.env.AGENTTRACE_SCREENSHOTS ??
          "../../../.tmp/agenttrace-20261023/screenshots",
        `sample-comparison-${size.width}.png`,
      ),
      fullPage: true,
    });
    await expect(
      page.getByText("Compatible scenario revision", { exact: false }),
    ).toBeVisible();
    await expect(
      page
        .getByRole("cell", { name: "completed · changed", exact: true })
        .first(),
    ).toBeVisible();
    await page
      .getByRole("button", { name: "Recorded playback", exact: true })
      .click();
    await expect(
      page
        .locator("main")
        .getByRole("button", { name: "Next step", exact: true }),
    ).toBeDisabled();
    await expect(page.getByText("Step 1 of 1", { exact: true })).toBeVisible();
    await guided
      .getByRole("button", { name: "Next step", exact: true })
      .click();
    await page
      .getByRole("link", { name: "request-19, failed", exact: true })
      .click();
    await expect(
      page.getByRole("region", { name: "Selected span" }),
    ).toContainText("exceeded its timeout");
    await page.getByRole("link", { name: "Runs", exact: true }).click();
    await page
      .getByRole("link", { name: "request-20, cancelled", exact: true })
      .click();
    await expect(
      page.getByRole("region", { name: "Selected span" }),
    ).toContainText("Request cancelled by the caller");
    await guided
      .getByRole("button", { name: "Next step", exact: true })
      .click();
    await expect(
      page.getByRole("heading", { name: "The actual project workflow" }),
    ).toBeVisible();
    await guided
      .getByRole("button", { name: "Finish tour", exact: true })
      .click();
    await expect(guided).toHaveCount(0);
    await page.getByRole("link", { name: "Costs", exact: true }).click();
    await expect(
      page.getByRole("heading", { name: "Costs", exact: true }),
    ).toBeVisible();
    await expect(page.getByText("Illustrative", { exact: true })).toBeVisible();
    await page.getByRole("link", { name: "Live", exact: true }).click();
    await expect(
      page.getByText("0 events shown", { exact: false }),
    ).toBeVisible();
    await page.getByRole("button", { name: "Step event", exact: true }).click();
    await expect(
      page.getByText("1 events shown", { exact: false }),
    ).toBeVisible();
    await page
      .getByRole("button", { name: "Reset playback", exact: true })
      .click();
    await expect(
      page.getByText("0 events shown", { exact: false }),
    ).toBeVisible();
    await page
      .getByRole("link", { name: "Actual workflow", exact: true })
      .click();
    await expect(
      page.getByRole("heading", { name: "The actual project workflow" }),
    ).toBeVisible();
    await page.getByRole("button", { name: "Reset demo", exact: true }).click();
    await page.getByLabel("Scenario", { exact: true }).selectOption("repaired");
    await expect(page.getByTestId("completed-count")).toHaveText("18");
    await page.getByRole("link", { name: "Runs", exact: true }).click();
    await expect(page.getByTestId("completed-count")).toHaveText("18");
    await page.getByRole("button", { name: "Reset demo", exact: true }).click();
    await expect(page.getByTestId("completed-count")).toHaveText("17");
    await expect(
      page.getByRole("region", { name: "Guided investigation" }),
    ).toHaveCount(0);
    for (const theme of ["light", "dark"]) {
      if (theme === "dark")
        await page.getByRole("button", { name: "Toggle theme" }).click();
      const contrasts = await page
        .locator(".outcome")
        .evaluateAll((elements) => {
          function luminance(color: string) {
            const values = (color.match(/[\d.]+/g) ?? [])
              .slice(0, 3)
              .map(Number)
              .map((value) => {
                value /= 255;
                return value <= 0.04045
                  ? value / 12.92
                  : ((value + 0.055) / 1.055) ** 2.4;
              });
            return values[0] * 0.2126 + values[1] * 0.7152 + values[2] * 0.0722;
          }
          return elements.map((element) => {
            const style = getComputedStyle(element);
            const pair = [
              luminance(style.color),
              luminance(style.backgroundColor),
            ].sort((a, b) => a - b);
            return {
              status: element.textContent,
              ratio: (pair[1] + 0.05) / (pair[0] + 0.05),
            };
          });
        });
      for (const contrast of contrasts)
        expect(
          contrast.ratio,
          `${theme} ${contrast.status} contrast`,
        ).toBeGreaterThanOrEqual(4.5);
    }
    await page.getByRole("button", { name: "Toggle theme" }).click();
    await page.keyboard.press("Tab");
    await expect(page.locator(":focus")).not.toHaveCount(0);
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
    await page.screenshot({
      path: path.resolve(
        process.env.AGENTTRACE_SCREENSHOTS ??
          "../../../.tmp/agenttrace-20261023/screenshots",
        `sample-overview-${size.width}.png`,
      ),
      fullPage: true,
    });
    expect(external).toEqual([]);
    expect(errors).toEqual([]);
  });
}

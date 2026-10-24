import { expect, test } from "@playwright/test";
const api = process.env.AGENTTRACE_API_URL ?? "http://127.0.0.1:8300";
test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem(
      "agenttrace.preferences.v1",
      JSON.stringify({ source: "connected" }),
    );
    sessionStorage.clear();
  });
  await page.goto("/");
  await expect(
    page.getByRole("button", { name: "Run bundled workload", exact: true }),
  ).toBeEnabled();
});
test("retry a failed launch after a previous completed job reuses the request UUID and actually launches", async ({
  page,
}) => {
  await page
    .getByRole("button", { name: "Run bundled workload", exact: true })
    .click();
  await expect(page.getByTestId("execution-status")).toContainText(
    "Execution completed",
    { timeout: 120000 },
  );
  const originalCohort = await page.getByTestId("cohort-select").inputValue();
  let failedRequest: { scenario: string; request_id: string } | undefined;
  await page.route(`${api}/api/portfolio/executions`, (route) => {
    if (route.request().method() === "POST") {
      failedRequest = route.request().postDataJSON();
      return route.abort();
    }
    return route.continue();
  });
  await page
    .getByRole("button", { name: "Run bundled workload", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Retry last request", exact: true }),
  ).toBeVisible();
  expect(failedRequest?.request_id).toMatch(/^[0-9a-f-]{36}$/);
  await page.unroute(`${api}/api/portfolio/executions`);
  const retryRequest = page.waitForRequest(
    (request) =>
      request.method() === "POST" &&
      request.url() === `${api}/api/portfolio/executions`,
    { timeout: 10000 },
  );
  await page
    .getByRole("button", { name: "Retry last request", exact: true })
    .click();
  const retried = await retryRequest;
  expect(retried.postDataJSON()).toEqual(failedRequest);
  await expect(page.getByTestId("execution-status")).toContainText(
    "Execution completed",
    { timeout: 120000 },
  );
  await expect(page.getByTestId("cohort-select")).not.toHaveValue(
    originalCohort,
  );
  await expect(page.getByTestId("run-count")).toHaveText("20");
});
test("retry status reads resumes polling without another workload launch", async ({
  page,
}) => {
  let posts = 0;
  page.on("request", (request) => {
    if (
      request.method() === "POST" &&
      request.url() === `${api}/api/portfolio/executions`
    )
      posts++;
  });
  await page.route(`${api}/api/portfolio/executions/*`, (route) =>
    route.abort(),
  );
  await page
    .getByRole("button", { name: "Run bundled workload", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Retry last request", exact: true }),
  ).toBeVisible();
  await page.unroute(`${api}/api/portfolio/executions/*`);
  const poll = page.waitForRequest(
    (request) =>
      request.method() === "GET" &&
      request.url().startsWith(`${api}/api/portfolio/executions/`),
    { timeout: 10000 },
  );
  await page
    .getByRole("button", { name: "Retry last request", exact: true })
    .click();
  await poll;
  await expect(page.getByTestId("execution-status")).toContainText(
    "Execution completed",
    { timeout: 120000 },
  );
  expect(posts).toBe(1);
  await expect(page.getByTestId("run-count")).toHaveText("20");
});

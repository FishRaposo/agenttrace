import { test, expect } from "@playwright/test";
import path from "node:path";

const api = process.env.AGENTTRACE_API_URL ?? "http://127.0.0.1:8300";
const shots =
  process.env.AGENTTRACE_SCREENSHOTS ??
  "../../../.tmp/agenttrace-20261023/screenshots";
type SavedRun = {
  id: string;
  name: string;
  status: string;
  span_count: number;
  total_cost: number;
  metadata: Record<string, unknown>;
};
test("real launch, persisted investigation, repair, costs, stream and outage recovery", async ({
  page,
  request,
}) => {
  const errors: string[] = [];
  let outage = false;
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("console", (message) => {
    if (message.type() !== "error") return;
    const expected =
      outage &&
      message.location().url.startsWith(api) &&
      message.text().includes("Failed to load resource");
    if (!expected)
      errors.push(`console: ${message.text()} at ${message.location().url}`);
  });
  await page.addInitScript(() => {
    if (!localStorage.getItem("agenttrace.preferences.v1"))
      localStorage.setItem(
        "agenttrace.preferences.v1",
        JSON.stringify({ source: "connected" }),
      );
  });
  await page.goto("/");
  await expect(page.getByTestId("source-select")).toHaveValue("connected");
  await page
    .getByLabel("Workload scenario", { exact: true })
    .selectOption("incident");
  await page
    .getByRole("button", { name: "Run bundled workload", exact: true })
    .click();
  await expect(page.getByTestId("execution-status")).toContainText(
    "Execution completed",
    { timeout: 120000 },
  );
  await expect(page.getByTestId("execution-status")).toContainText(
    "complete delivery confirmed",
  );
  await expect(page.getByTestId("run-count")).toHaveText("20");
  await expect(page.getByTestId("completed-count")).toHaveText("17");
  const cohort = await page.getByTestId("cohort-select").inputValue();
  expect(cohort).toMatch(/^[0-9a-f-]{36}$/);
  const stored = await request.get(
    `${api}/api/runs?limit=100&cohort_id=${cohort}`,
  );
  expect(stored.ok()).toBe(true);
  const incident = (await stored.json()).runs as SavedRun[];
  expect(incident).toHaveLength(20);
  expect(incident.filter((run) => run.status === "failed")).toHaveLength(2);
  expect(incident.filter((run) => run.status === "cancelled")).toHaveLength(1);
  const retrieval = incident.find(
    (run) => run.metadata.case_id === "request-18",
  )!;
  expect(retrieval.status).toBe("failed");
  for (const run of incident) {
    const spans = await request.get(`${api}/api/runs/${run.id}/spans`);
    expect((await spans.json()).length).toBe(run.span_count);
  }
  await page.goto(`/runs/${retrieval.id}`);
  await expect(
    page.getByRole("heading", { name: "Request timeline" }),
  ).toBeVisible();
  await expect(
    page.getByRole("region", { name: "Selected span" }),
  ).toContainText(/retrieval|source|fault/i);
  await page.reload();
  await expect(
    page.getByRole("heading", { name: "Request timeline" }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Recorded playback", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Recorded playback", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Next step", exact: true }),
  ).toBeDisabled();
  await expect(page.getByText("Step 1 of 1", { exact: true })).toBeVisible();
  await page.getByRole("link", { name: "Overview", exact: true }).click();
  await page
    .getByLabel("Workload scenario", { exact: true })
    .selectOption("repaired");
  await page
    .getByRole("button", { name: "Run bundled workload", exact: true })
    .click();
  await expect(page.getByTestId("execution-status")).toContainText(
    "Execution completed",
    { timeout: 120000 },
  );
  await expect(page.getByTestId("completed-count")).toHaveText("18");
  const repairedCohort = await page.getByTestId("cohort-select").inputValue();
  expect(repairedCohort).not.toBe(cohort);
  const repairedResponse = await request.get(
    `${api}/api/runs?limit=100&cohort_id=${repairedCohort}`,
  );
  const repaired = (await repairedResponse.json()).runs as SavedRun[];
  const fixed = repaired.find((run) => run.metadata.case_id === "request-18")!;
  expect(fixed.status).toBe("completed");
  expect(repaired.filter((run) => run.status === "failed")).toHaveLength(1);
  expect(repaired.filter((run) => run.status === "cancelled")).toHaveLength(1);
  await page.goto(`/runs/${retrieval.id}`);
  await page
    .getByRole("button", { name: "Compare repair", exact: true })
    .click();
  await page.getByLabel("Compare with", { exact: true }).fill(fixed.id);
  await expect(
    page.getByText("Compatible scenario revision", { exact: false }),
  ).toBeVisible();
  await expect(
    page
      .getByRole("cell", { name: "completed · changed", exact: true })
      .first(),
  ).toBeVisible();
  await page.screenshot({
    path: path.resolve(shots, "connected-comparison.png"),
    fullPage: true,
  });
  await page.getByRole("link", { name: "Costs", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Costs", exact: true }),
  ).toBeVisible();
  await expect(page.getByText("illustrative", { exact: true })).toBeVisible();
  await page.getByRole("link", { name: "Live", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Live", exact: true }),
  ).toBeVisible();
  await expect(page.locator(".event-list li").first()).toBeVisible();
  await expect(page.locator(".event-list li")).toHaveCount(58);
  const cursor = await page
    .locator(".event-list li")
    .last()
    .getAttribute("data-delivery-cursor");
  expect(Number(cursor)).toBeGreaterThan(0);
  await page.getByRole("button", { name: "Pause", exact: true }).click();
  const resumed = page.waitForRequest(
    (request) =>
      request.url().includes("/api/stream/traces") &&
      new URL(request.url()).searchParams.get("cursor") === cursor,
  );
  await page
    .getByRole("button", { name: "Play / resume", exact: true })
    .click();
  await resumed;
  await expect(page.locator(".event-list li")).toHaveCount(58);
  const launch = await request.post(`${api}/api/portfolio/executions`, {
    data: { scenario: "incident", request_id: crypto.randomUUID() },
  });
  expect(launch.status()).toBe(202);
  const liveJob = await launch.json();
  await expect
    .poll(
      async () => {
        const response = await request.get(
          `${api}/api/portfolio/executions/${liveJob.id}`,
        );
        return (await response.json()).status;
      },
      { timeout: 120000 },
    )
    .toBe("completed");
  // The selected cohort is repaired, so new incident events must not contaminate it.
  await expect(page.getByTestId("cohort-select")).toHaveValue(repairedCohort);
  await page.getByTestId("cohort-select").selectOption("");
  await expect(page.locator(".event-list li").first()).toBeVisible();
  const finalLive = await (
    await request.get(`${api}/api/portfolio/executions/${liveJob.id}`)
  ).json();
  await expect(
    page
      .locator(`.event-list li[data-run-id="${finalLive.run_ids[0]}"]`)
      .first(),
  ).toBeVisible({ timeout: 60000 });
  console.log(
    "Observed durable SSE resume cursor",
    cursor,
    "and live cohort",
    finalLive.cohort_id,
  );
  for (const size of [
    { width: 390, height: 844 },
    { width: 768, height: 1024 },
    { width: 1440, height: 900 },
  ]) {
    await page.setViewportSize(size);
    await page.emulateMedia({ reducedMotion: "reduce" });
    for (const route of [
      "/",
      "/runs",
      `/runs/${fixed.id}`,
      "/costs",
      "/live",
      "/workflow",
    ]) {
      await page.goto(route);
      await expect(page.locator("main h1")).toBeVisible();
      await expect(page.locator("nextjs-portal")).toHaveCount(0);
      expect(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= innerWidth,
        ),
      ).toBe(true);
    }
    await page.goto(`/runs/${fixed.id}`);
    await expect(
      page.getByRole("heading", { name: "Request timeline" }),
    ).toBeVisible();
    const answerStage = page
      .getByRole("list", { name: "Ordered text stages" })
      .getByRole("button")
      .nth(1);
    await answerStage.focus();
    await expect(answerStage).toBeFocused();
    await expect(answerStage).toHaveAttribute("aria-pressed", "false");
    await page.keyboard.press("Enter");
    await expect(answerStage).toHaveAttribute("aria-pressed", "true");
    await expect(
      page
        .getByRole("region", { name: "Selected span" })
        .getByRole("heading", { name: "answer", exact: true }),
    ).toBeVisible();
    await page
      .getByText("Capture summaries, arguments and results", { exact: true })
      .click();
    await expect(
      page.getByRole("region", { name: "Selected span" }),
    ).toContainText("metadata_only");
    await page.goto(`/runs/${retrieval.id}`);
    await expect(
      page.getByRole("heading", { name: "Request timeline" }),
    ).toBeVisible();
    await page.screenshot({
      path: path.resolve(shots, `connected-detail-${size.width}.png`),
      fullPage: true,
    });
  }
  for (const doc of [
    "portfolio-connected",
    "portfolio-verification",
    "portfolio-case-study",
  ]) {
    const response = await request.get(`/evidence/${doc}.md`);
    expect(response.status()).toBe(200);
    expect((await response.text()).length).toBeGreaterThan(500);
  }
  if (process.env.AGENTTRACE_LEGACY_RUN_ID) {
    await page.goto(`/runs/${process.env.AGENTTRACE_LEGACY_RUN_ID}`);
    await expect(page.locator("main")).toContainText("Pricing: unknown");
    await expect(page.locator("main")).toContainText("Scenario: unknown");
  }
  outage = true;
  await page.route(`${api}/**`, (route) => route.abort());
  await page.goto("/runs");
  await expect(page.getByRole("alert").first()).toContainText(
    "Collector connection unavailable",
  );
  await expect(page.getByTestId("source-select")).toHaveValue("connected");
  await page.unroute(`${api}/**`);
  await page
    .getByRole("button", { name: "Retry", exact: true })
    .first()
    .click();
  await expect(page.getByTestId("run-row").first()).toBeVisible();
  outage = false;
  await page.getByTestId("source-select").selectOption("sample");
  await expect(page.getByTestId("demo-mode-banner")).toContainText(
    "Interactive sample data",
  );
  await expect(page.getByTestId("run-count")).toHaveText("20");
  await page.getByTestId("source-select").selectOption("connected");
  await expect(page.getByTestId("source-select")).toHaveValue("connected");
  await page.getByTestId("cohort-select").selectOption("");
  await page.reload();
  await expect(page.getByTestId("source-select")).toHaveValue("connected");
  await expect(page.getByTestId("cohort-select")).toHaveValue("");
  expect(errors).toEqual([]);
});

import { describe, expect, it } from "vitest";
import { sampleCohort, sampleResponse } from "./demo-scenarios";
import {
  getPortfolioState,
  resetSample,
  setPortfolio,
} from "./portfolio-state";
describe("coherent twenty request scenarios", () => {
  it("shows exactly the declared incident outcomes and preserves case correlation", () => {
    const data = sampleCohort("incident");
    expect(data.runs.filter((r) => r.status === "completed")).toHaveLength(17);
    expect(data.spans).toHaveLength(56);
    expect(data.runs.filter((r) => r.status === "failed")).toHaveLength(2);
    expect(data.runs.filter((r) => r.status === "cancelled")).toHaveLength(1);
    expect(new Set(data.runs.map((r) => r.correlation_id)).size).toBe(20);
    expect(
      data.spans.every((s) => data.runs.some((r) => r.id === s.run_id)),
    ).toBe(true);
  });
  it("repairs retrieval only, retains timeout and cancellation", () => {
    const data = sampleCohort("repaired");
    expect(data.runs.filter((r) => r.status === "completed")).toHaveLength(18);
    expect(data.spans).toHaveLength(58);
    expect(data.runs[18].status).toBe("failed");
    expect(data.runs[19].status).toBe("cancelled");
    expect(
      data.spans.find(
        (s) => s.run_id.endsWith("request-18") && s.name === "retrieve",
      )?.status,
    ).toBe("completed");
  });
  it("reconciles costs, token counts and spans with exact recorded rows", () => {
    const data = sampleCohort("incident");
    for (const run of data.runs) {
      const spans = data.spans.filter((s) => s.run_id === run.id);
      expect(spans).toHaveLength(run.span_count);
      expect(spans.reduce((sum, s) => sum + (s.cost_usd ?? 0), 0)).toBe(
        run.total_cost,
      );
      expect(
        spans.reduce((sum, s) => sum + (s.token_usage?.total_tokens ?? 0), 0),
      ).toBe(run.total_tokens);
    }
  });
  it("playback is deterministic and contains unique fixed events", () => {
    const first = sampleCohort("incident").events;
    expect(sampleCohort("incident").events).toEqual(first);
    expect(new Set(first.map((s) => s.id)).size).toBe(first.length);
    expect(first.map((s) => s.start_time)).toEqual(
      [...first.map((s) => s.start_time)].sort(),
    );
  });
  it("reset restores the scenario and tour together without changing real cohort history", () => {
    setPortfolio({
      source: "sample",
      scenario: "repaired",
      tour: 3,
      cohort: "actual-cohort",
    });
    resetSample();
    expect(getPortfolioState()).toMatchObject({
      source: "sample",
      scenario: "incident",
      tour: -1,
      cohort: "actual-cohort",
    });
  });
  it("does not fabricate a run for unknown IDs", () => {
    expect(
      sampleResponse("/api/runs/not-recorded", "incident"),
    ).toBeUndefined();
  });
});

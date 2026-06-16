import { describe, it, expect } from "vitest";
import {
  demoResponseFor,
  demoRuns,
  demoStats,
  demoSpans,
  demoReplay,
  demoRunDiff,
} from "@/lib/demoData";
import type { RunListResponse } from "@/types";

describe("demoResponseFor", () => {
  it("resolves stats", () => {
    expect(demoResponseFor("/api/stats")).toEqual(demoStats);
  });

  it("resolves a paginated run list", () => {
    const res = demoResponseFor("/api/runs?limit=5") as RunListResponse;
    expect(res.runs).toHaveLength(demoRuns.length);
    expect(res.total).toBe(demoRuns.length);
  });

  it("resolves a single run by id", () => {
    const run = demoResponseFor("/api/runs/demo-run-002");
    expect(run).toMatchObject({ id: "demo-run-002", name: "support-triage" });
  });

  it("falls back to first run for an unknown id", () => {
    const run = demoResponseFor("/api/runs/unknown") as { id: string };
    expect(run.id).toBe(demoRuns[0].id);
  });

  it("resolves spans for a run", () => {
    const spans = demoResponseFor("/api/runs/demo-run-001/spans") as unknown[];
    expect(spans.length).toBeGreaterThan(0);
  });

  it("resolves cost summary with breakdowns", () => {
    const summary = demoResponseFor("/api/costs/summary") as {
      by_provider: Record<string, number>;
    };
    expect(Object.keys(summary.by_provider)).toContain("openai");
  });

  it("resolves cost-by-provider as an array", () => {
    const rows = demoResponseFor("/api/costs/by-provider") as unknown[];
    expect(Array.isArray(rows)).toBe(true);
    expect(rows.length).toBeGreaterThan(0);
  });

  it("resolves the health endpoint", () => {
    expect(demoResponseFor("/health")).toMatchObject({ status: "demo" });
  });

  it("returns undefined for an unmapped path", () => {
    expect(demoResponseFor("/api/nonexistent")).toBeUndefined();
  });
});

describe("demo derived helpers", () => {
  it("builds a replay payload from a run", () => {
    const replay = demoReplay(demoRuns[0]);
    expect(replay.run.id).toBe(demoRuns[0].id);
    expect(replay.total_steps).toBe(demoSpans.length);
  });

  it("builds a run diff with computed differences", () => {
    const diff = demoRunDiff(demoRuns[0], demoRuns[3]);
    expect(diff.differences.cost_diff).toBeCloseTo(
      demoRuns[3].total_cost - demoRuns[0].total_cost
    );
  });
});

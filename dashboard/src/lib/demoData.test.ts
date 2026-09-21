import { describe, it, expect } from "vitest";
import {
  demoResponseFor,
  demoRuns,
  demoStats,
  demoSpansForRun,
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

  it("resolves the issue-to-pr showcase run", () => {
    const run = demoResponseFor("/api/runs/demo-run-005") as { id: string; name: string };
    expect(run).toMatchObject({ id: "demo-run-005", name: "issue-to-draft-pr" });
  });

  it("resolves spans for the issue-to-pr run", () => {
    const spans = demoResponseFor("/api/runs/demo-run-005/spans") as { name: string }[];
    expect(spans.some((s) => s.name === "draft-pr-intent")).toBe(true);
  });

  it("resolves run diff queries", () => {
    const diff = demoResponseFor(
      "/api/diff/runs?run_id_1=demo-run-005&run_id_2=demo-run-001"
    ) as { run1: { id: string }; run2: { id: string } };
    expect(diff.run1.id).toBe("demo-run-005");
    expect(diff.run2.id).toBe("demo-run-001");
  });

  it("resolves budget status", () => {
    const status = demoResponseFor("/api/budgets/demo-budget-1/status") as {
      budget_id: string;
    };
    expect(status.budget_id).toBe("demo-budget-1");
  });
});

describe("demo derived helpers", () => {
  it("builds a replay payload from a run", () => {
    const replay = demoReplay(demoRuns[0]);
    expect(replay.run.id).toBe(demoRuns[0].id);
    expect(replay.total_steps).toBe(demoSpansForRun(demoRuns[0].id).length);
  });

  it("builds a run diff with computed differences", () => {
    const diff = demoRunDiff(demoRuns[0], demoRuns[3]);
    expect(diff.differences.cost_diff).toBeCloseTo(
      demoRuns[3].total_cost - demoRuns[0].total_cost
    );
  });
});

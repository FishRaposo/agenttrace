/**
 * Demo-mode fixtures.
 *
 * When the AgentTrace backend is unreachable, the API client falls back to this
 * deterministic in-memory dataset so the dashboard remains fully explorable with
 * no server running (useful for previews, screenshots, and offline development).
 * A visible banner is shown whenever demo data is being served.
 */

import type {
  Budget,
  BudgetStatus,
  CostSummary,
  CostTimeseries,
  HealthResponse,
  ModelCostBreakdown,
  ReplayData,
  Run,
  RunDiff,
  RunListResponse,
  Stats,
  TraceResponse,
} from "@/types";

const BASE_TIME = Date.UTC(2026, 0, 15, 12, 0, 0);

function isoOffset(minutes: number): string {
  return new Date(BASE_TIME + minutes * 60_000).toISOString();
}

export const demoRuns: Run[] = [
  {
    id: "demo-run-001",
    correlation_id: "wf-research",
    name: "research-agent",
    status: "completed",
    start_time: isoOffset(-30),
    end_time: isoOffset(-28),
    total_cost: 0.0421,
    total_tokens: 18432,
    span_count: 12,
    metadata: { agent: "research", env: "demo" },
  },
  {
    id: "demo-run-002",
    correlation_id: "wf-support",
    name: "support-triage",
    status: "running",
    start_time: isoOffset(-12),
    end_time: null,
    total_cost: 0.0117,
    total_tokens: 5120,
    span_count: 5,
    metadata: { agent: "support", env: "demo" },
  },
  {
    id: "demo-run-003",
    correlation_id: "wf-research",
    name: "summarizer",
    status: "failed",
    start_time: isoOffset(-90),
    end_time: isoOffset(-89),
    total_cost: 0.0033,
    total_tokens: 1980,
    span_count: 3,
    metadata: { agent: "summarizer", env: "demo" },
  },
  {
    id: "demo-run-004",
    correlation_id: "wf-batch",
    name: "nightly-batch",
    status: "completed",
    start_time: isoOffset(-240),
    end_time: isoOffset(-220),
    total_cost: 0.318,
    total_tokens: 142000,
    span_count: 47,
    metadata: { agent: "batch", env: "demo" },
  },
];

export const demoStats: Stats = {
  total_runs: demoRuns.length,
  total_cost: demoRuns.reduce((s, r) => s + r.total_cost, 0),
  total_tokens: demoRuns.reduce((s, r) => s + r.total_tokens, 0),
  avg_duration_ms: 842.5,
};

export const demoSpans: TraceResponse[] = [
  {
    id: "demo-span-1",
    run_id: "demo-run-001",
    span_id: "s1",
    parent_span_id: null,
    span_type: "decision",
    name: "plan-research",
    input_data: { goal: "Summarize Q4 earnings" },
    output_data: { steps: 3 },
    metadata: { feature: "planning" },
    start_time: isoOffset(-30),
    end_time: isoOffset(-30),
    duration_ms: 120,
    cost_usd: 0.0008,
    token_usage: { prompt_tokens: 220, completion_tokens: 80, total_tokens: 300 },
    status: "completed",
    error: null,
  },
  {
    id: "demo-span-2",
    run_id: "demo-run-001",
    span_id: "s2",
    parent_span_id: "s1",
    span_type: "tool_call",
    name: "web_search",
    input_data: { query: "Q4 earnings report" },
    output_data: { results: 8 },
    metadata: { tool_name: "web_search" },
    start_time: isoOffset(-30),
    end_time: isoOffset(-29),
    duration_ms: 540,
    cost_usd: 0,
    token_usage: null,
    status: "completed",
    error: null,
  },
  {
    id: "demo-span-3",
    run_id: "demo-run-001",
    span_id: "s3",
    parent_span_id: "s1",
    span_type: "llm_call",
    name: "gpt-4o synthesis",
    input_data: { prompt: "Synthesize findings" },
    output_data: { summary: "..." },
    metadata: { feature: "synthesis" },
    start_time: isoOffset(-29),
    end_time: isoOffset(-28),
    duration_ms: 1340,
    cost_usd: 0.0405,
    token_usage: {
      prompt_tokens: 12000,
      completion_tokens: 6132,
      total_tokens: 18132,
    },
    status: "completed",
    error: null,
  },
];

export const demoCostSummary: CostSummary = {
  total_cost: demoStats.total_cost,
  total_tokens: demoStats.total_tokens,
  total_spans: demoRuns.reduce((s, r) => s + r.span_count, 0),
  by_provider: { openai: 0.291, anthropic: 0.084 },
  by_model: { "gpt-4o": 0.291, "claude-3-5-sonnet": 0.084 },
  by_feature: { synthesis: 0.21, planning: 0.09, retrieval: 0.075 },
  by_prompt_version: { "summarize-v1": 0.147, "summarize-v2": 0.228 },
};

export const demoDailyCostReport = {
  days: {
    "2026-08-10": {
      total_requests: 8,
      total_tokens: 32600,
      input_tokens: 20100,
      output_tokens: 12500,
      estimated_cost: 0.147,
      average_latency_ms: 812.5,
      p50_latency_ms: 760,
      p95_latency_ms: 1280,
      p99_latency_ms: 1390,
      error_rate: 0,
      cost_by_model: { "gpt-4o": 0.147 },
      cost_by_prompt_version: { "summarize-v1": 0.147 },
    },
    "2026-08-11": {
      total_requests: 11,
      total_tokens: 49100,
      input_tokens: 29200,
      output_tokens: 19900,
      estimated_cost: 0.228,
      average_latency_ms: 745.45,
      p50_latency_ms: 710,
      p95_latency_ms: 1190,
      p99_latency_ms: 1265,
      error_rate: 0.0909,
      cost_by_model: { "gpt-4o": 0.144, "claude-3-5-sonnet": 0.084 },
      cost_by_prompt_version: { "summarize-v2": 0.228 },
    },
  },
};

export const demoCostTimeseries: CostTimeseries = {
  granularity: "day",
  data: Array.from({ length: 7 }, (_, i) => ({
    bucket: new Date(BASE_TIME - (6 - i) * 86_400_000).toISOString().slice(0, 10),
    cost: 0.02 + i * 0.015,
    tokens: 5000 + i * 3200,
    spans: 4 + i,
  })),
};

export const demoCostByModel: ModelCostBreakdown[] = [
  {
    model: "gpt-4o",
    total_cost: 0.291,
    total_tokens: 120000,
    span_count: 30,
    avg_latency_ms: 980,
  },
  {
    model: "claude-3-5-sonnet",
    total_cost: 0.084,
    total_tokens: 47432,
    span_count: 17,
    avg_latency_ms: 720,
  },
];

export const demoHealth: HealthResponse = {
  status: "demo",
  service: "agenttrace-demo",
};

export const demoBudgets: Budget[] = [
  {
    id: "demo-budget-1",
    name: "Monthly LLM",
    scope: "global",
    scope_value: null,
    limit_usd: 50,
    period: "monthly",
    alert_threshold_pct: 80,
    created_at: isoOffset(-1440),
  },
];

export const demoBudgetStatus: BudgetStatus = {
  budget_id: "demo-budget-1",
  name: "Monthly LLM",
  limit_usd: 50,
  current_cost: 12.4,
  remaining: 37.6,
  percent_used: 24.8,
  alert_triggered: false,
  breached: false,
  projected_monthly: 26.1,
};

export function demoRunDiff(run1: Run, run2: Run): RunDiff {
  const slim = (r: Run) => ({
    id: r.id,
    name: r.name,
    status: r.status,
    total_cost: r.total_cost,
    total_tokens: r.total_tokens,
    span_count: r.span_count,
    start_time: r.start_time,
    end_time: r.end_time,
  });
  return {
    run1: slim(run1),
    run2: slim(run2),
    differences: {
      cost_diff: run2.total_cost - run1.total_cost,
      token_diff: run2.total_tokens - run1.total_tokens,
      span_count_diff: run2.span_count - run1.span_count,
      duration_diff: 0,
    },
    spans: { only_in_run1: [], only_in_run2: [], common_count: 0, differences: [] },
  };
}

export function demoReplay(run: Run): ReplayData {
  return {
    run: {
      id: run.id,
      name: run.name,
      status: run.status,
      start_time: run.start_time,
      end_time: run.end_time,
      metadata: run.metadata,
    },
    steps: demoSpans.map((s) => ({
      id: s.id,
      name: s.name,
      span_type: s.span_type,
      input_data: s.input_data,
      output_data: s.output_data,
      metadata: s.metadata,
      start_time: s.start_time,
      end_time: s.end_time,
      status: s.status,
      error: s.error,
    })),
    total_steps: demoSpans.length,
  };
}

/**
 * Resolve a demo response for a given API path. Returns ``undefined`` when no
 * fixture matches, letting the caller surface a normal error instead.
 */
export function demoResponseFor(path: string): unknown {
  const clean = path.split("?")[0];

  if (clean === "/api/stats") return demoStats;
  if (clean === "/health") return demoHealth;
  if (clean === "/api/costs/summary") return demoCostSummary;
  if (clean === "/api/costs/reports/daily") return demoDailyCostReport;
  if (clean.startsWith("/api/costs/timeseries")) return demoCostTimeseries;
  if (clean === "/api/costs/by-model") return demoCostByModel;
  if (clean === "/api/costs/by-provider") {
    return Object.entries(demoCostSummary.by_provider).map(([provider, total]) => ({
      provider,
      total_cost: total,
      span_count: 12,
    }));
  }
  if (clean === "/api/costs/by-feature") {
    return Object.entries(demoCostSummary.by_feature).map(([feature, total]) => ({
      feature,
      total_cost: total,
      span_count: 8,
    }));
  }
  if (clean === "/api/costs/top-runs") {
    return [...demoRuns]
      .sort((a, b) => b.total_cost - a.total_cost)
      .map((r) => ({
        id: r.id,
        name: r.name,
        total_cost: r.total_cost,
        total_tokens: r.total_tokens,
        span_count: r.span_count,
        status: r.status,
        start_time: r.start_time,
      }));
  }
  if (clean === "/api/costs/projection") {
    return {
      trailing_7d_cost: 0.21,
      trailing_30d_cost: 0.78,
      daily_burn: 0.03,
      monthly_projection: 0.9,
    };
  }
  if (clean === "/api/budgets") return demoBudgets;

  if (clean === "/api/runs") {
    const response: RunListResponse = {
      runs: demoRuns,
      total: demoRuns.length,
      limit: 20,
      offset: 0,
    };
    return response;
  }

  // /api/runs/{id}/spans
  const spansMatch = clean.match(/^\/api\/runs\/([^/]+)\/spans$/);
  if (spansMatch) {
    return demoSpans.filter((s) => s.run_id === spansMatch[1]);
  }

  // /api/runs/{id}
  const runMatch = clean.match(/^\/api\/runs\/([^/]+)$/);
  if (runMatch) {
    return demoRuns.find((r) => r.id === runMatch[1]) ?? demoRuns[0];
  }

  // /api/replay/runs/{id}
  const replayMatch = clean.match(/^\/api\/replay\/runs\/([^/]+)$/);
  if (replayMatch) {
    const run = demoRuns.find((r) => r.id === replayMatch[1]) ?? demoRuns[0];
    return demoReplay(run);
  }

  return undefined;
}

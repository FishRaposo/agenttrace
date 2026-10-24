/** Fixed, inspectable sample telemetry. No requests or clocks are involved. */
import type { Run, RunDiff, TraceResponse } from "@/types";

export type Scenario = "incident" | "repaired";
export const SCENARIO_REVISION = "agenttrace-portfolio-2026-10-23-v1";
const BASE = Date.UTC(2026, 9, 23, 12);
export const scenarios = [
  {
    id: "incident",
    name: "Incident",
    description: "17 completed · retrieval failure · timeout · cancellation",
  },
  {
    id: "repaired",
    name: "Repaired",
    description: "18 completed · timeout and cancellation remain",
  },
] as const;

export function sampleCohort(scenario: Scenario) {
  const spans: TraceResponse[] = [];
  const runs: Run[] = Array.from({ length: 20 }, (_, index) => {
    const caseId = `request-${String(index + 1).padStart(2, "0")}`;
    const id = `sample-${scenario}-${caseId}`;
    const failed = (index === 17 && scenario === "incident") || index === 18;
    const cancelled = index === 19;
    const start = BASE + index * 3;
    const stages = ["retrieve", "answer", "validate"];
    const endStage =
      index === 17 && failed ? 0 : index === 18 || cancelled ? 1 : 2;
    let elapsed = 0;
    const runSpans = stages
      .slice(0, endStage + 1)
      .map((stage, occurrence): TraceResponse => {
        const error = failed && occurrence === endStage;
        const duration =
          stage === "answer"
            ? error
              ? 120
              : 44
            : stage === "retrieve"
              ? 18
              : 6;
        const stageStart = start + elapsed;
        elapsed += duration;
        return {
          id: `${id}-${stage}`,
          span_id: `${id}-${stage}`,
          run_id: id,
          parent_span_id: null,
          name: stage,
          span_type:
            stage === "answer"
              ? "llm_call"
              : stage === "retrieve"
                ? "retrieval"
                : "decision",
          status:
            cancelled && occurrence === endStage
              ? "cancelled"
              : error
                ? "error"
                : "completed",
          start_time: new Date(stageStart).toISOString(),
          end_time: new Date(start + elapsed).toISOString(),
          duration_ms: duration,
          input_data: {
            captured: false,
            size_bytes: stage === "retrieve" ? 48 : 24,
          },
          output_data: { captured: false, size_bytes: error ? 0 : 64 },
          metadata: {
            cohort_id: `sample-${scenario}`,
            case_id: caseId,
            stage_key: stage,
            attempt: 1,
            scenario,
            scenario_revision: SCENARIO_REVISION,
            provider_origin: "synthetic",
            usage_origin: "synthetic",
            pricing_origin: "illustrative",
            pricing_revision: "illustrative-2026-10-23-v1",
            capture_policy: "metadata only",
            cancellation: cancelled && occurrence === endStage,
          },
          cost_usd: stage === "answer" && !error && !cancelled ? 0.0002 : 0,
          token_usage:
            stage === "answer" && !error && !cancelled
              ? { prompt_tokens: 120, completion_tokens: 40, total_tokens: 160 }
              : null,
          error: error
            ? index === 17
              ? "Retrieval returned no matching source. The request stopped before model generation."
              : "Synthetic provider exceeded its timeout. Retrieval succeeded; generation did not complete."
            : cancelled && occurrence === endStage
              ? "Request cancelled by the caller; no response was completed."
              : null,
        };
      });
    spans.push(...runSpans);
    return {
      id,
      correlation_id: `correlation-${caseId}`,
      name: caseId,
      status: cancelled ? "cancelled" : failed ? "failed" : "completed",
      start_time: new Date(start).toISOString(),
      end_time: runSpans.at(-1)!.end_time,
      total_cost: runSpans.reduce((sum, span) => sum + (span.cost_usd ?? 0), 0),
      total_tokens: runSpans.reduce(
        (sum, span) => sum + (span.token_usage?.total_tokens ?? 0),
        0,
      ),
      span_count: runSpans.length,
      metadata: {
        cohort_id: `sample-${scenario}`,
        case_id: caseId,
        scenario,
        scenario_revision: SCENARIO_REVISION,
        pricing_origin: "illustrative",
        pricing_revision: "illustrative-2026-10-23-v1",
        execution_origin: "interactive_sample",
        provider_origin: "synthetic",
        usage_origin: "synthetic",
      },
    };
  });
  return {
    runs,
    spans,
    events: [...spans].sort(
      (a, b) =>
        a.start_time.localeCompare(b.start_time) ||
        a.span_id.localeCompare(b.span_id),
    ),
  };
}

export function sampleResponse(path: string, scenario: Scenario): unknown {
  const url = new URL(path, "http://sample.local");
  const data = sampleCohort(scenario);
  // Historical sample links are intentionally independent from the chosen cohort.
  const all = [
    ...sampleCohort("incident").runs,
    ...sampleCohort("repaired").runs,
  ];
  const allSpans = [
    ...sampleCohort("incident").spans,
    ...sampleCohort("repaired").spans,
  ];
  if (url.pathname === "/api/runs") {
    let rows = data.runs;
    const status = url.searchParams.get("status");
    const search = url.searchParams.get("search");
    if (status) rows = rows.filter((run) => run.status === status);
    if (search)
      rows = rows.filter((run) => `${run.name} ${run.id}`.includes(search));
    const offset = Number(url.searchParams.get("offset") ?? 0);
    const limit = Number(url.searchParams.get("limit") ?? 100);
    return {
      runs: rows.slice(offset, offset + limit),
      total: rows.length,
      limit,
      offset,
    };
  }
  const match = url.pathname.match(/^\/api\/runs\/([^/]+)(\/spans)?$/);
  if (match)
    return match[2]
      ? allSpans.filter((span) => span.run_id === match[1])
      : all.find((run) => run.id === match[1]);
  if (url.pathname === "/api/stats")
    return {
      total_runs: data.runs.length,
      total_cost: data.runs.reduce((s, r) => s + r.total_cost, 0),
      total_tokens: data.runs.reduce((s, r) => s + r.total_tokens, 0),
      avg_duration_ms: 86,
    };
  if (url.pathname === "/api/costs/summary")
    return {
      total_cost: data.runs.reduce((s, r) => s + r.total_cost, 0),
      total_tokens: data.runs.reduce((s, r) => s + r.total_tokens, 0),
      total_spans: data.spans.length,
      by_provider: {
        "synthetic-provider": data.runs.reduce((s, r) => s + r.total_cost, 0),
      },
      by_model: {
        "synthetic-model": data.runs.reduce((s, r) => s + r.total_cost, 0),
      },
      by_feature: {},
      by_prompt_version: {},
    };
  if (url.pathname.startsWith("/api/replay/runs/")) {
    const run = all.find((run) => run.id === url.pathname.split("/").at(-1));
    if (!run) return undefined;
    const steps = allSpans.filter((span) => span.run_id === run.id);
    return { run, steps, total_steps: steps.length };
  }
  if (url.pathname === "/api/diff/runs") {
    const run1 = all.find((run) => run.id === url.searchParams.get("run_id_1"));
    const run2 = all.find((run) => run.id === url.searchParams.get("run_id_2"));
    if (!run1 || !run2) return undefined;
    const left = allSpans.filter((span) => span.run_id === run1.id);
    const right = allSpans.filter((span) => span.run_id === run2.id);
    const keys = [...new Set([...left, ...right].map((span) => span.name))];
    return {
      run1,
      run2,
      differences: {
        cost_diff: run2.total_cost - run1.total_cost,
        token_diff: run2.total_tokens - run1.total_tokens,
        span_count_diff: run2.span_count - run1.span_count,
        duration_diff: 0,
      },
      spans: {
        only_in_run1: [],
        only_in_run2: [],
        common_count: left.filter((a) => right.some((b) => b.name === a.name))
          .length,
        differences: [],
      },
      compatibility: {
        compatible: true,
        reason: "Same fixed scenario revision; synthetic comparison.",
      },
      aligned_stages: keys.map((key) => {
        const a = left.find((span) => span.name === key);
        const b = right.find((span) => span.name === key);
        return {
          stage_key: key,
          occurrence: 1,
          attempt: 1,
          name: key,
          span_type: a?.span_type ?? b!.span_type,
          status_1: a?.status ?? null,
          status_2: b?.status ?? null,
          status_changed: a?.status !== b?.status,
        };
      }),
    } as RunDiff;
  }
  return undefined;
}

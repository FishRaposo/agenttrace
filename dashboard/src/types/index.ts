/**
 * Type definitions for the AgentTrace dashboard.
 */

export interface TokenUsage {
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
}

export interface CostBreakdown {
  span_type: SpanType;
  cost_usd: number;
  span_count: number;
}

export interface TimelineEvent {
  id: string;
  name: string;
  span_type: SpanType;
  start_time: string;
  end_time: string | null;
  duration_ms: number | null;
  status: SpanStatus;
  error: string | null;
}

export type RunStatus = "running" | "completed" | "failed" | "cancelled";

export type SpanType = "llm_call" | "tool_call" | "decision" | "retrieval" | "custom";

export type SpanStatus = "started" | "completed" | "error";

export interface Run {
  id: string;
  correlation_id: string | null;
  name: string;
  status: RunStatus;
  start_time: string;
  end_time: string | null;
  total_cost: number;
  total_tokens: number;
  span_count: number;
  metadata: Record<string, unknown> | null;
}

export interface RunListResponse {
  runs: Run[];
  total: number;
  limit: number;
  offset: number;
}

export interface Span {
  id: string;
  run_id: string;
  parent_span_id: string | null;
  name: string;
  span_type: SpanType;
  status: SpanStatus;
  input_data: unknown;
  output_data: unknown;
  metadata: Record<string, unknown> | null;
  start_time: string;
  end_time: string | null;
  duration_ms: number | null;
  cost_usd: number | null;
  token_usage: TokenUsage | null;
  error: string | null;
}

export interface TraceResponse {
  id: string;
  run_id: string;
  span_id: string;
  span_type: SpanType;
  name: string;
  input_data: unknown;
  output_data: unknown;
  metadata: Record<string, unknown> | null;
  start_time: string;
  end_time: string | null;
  duration_ms: number | null;
  cost_usd: number | null;
  token_usage: TokenUsage | null;
  status: SpanStatus;
  error: string | null;
}

export interface Stats {
  total_runs: number;
  total_cost: number;
  total_tokens: number;
  avg_duration_ms: number;
}

export interface HealthResponse {
  status: string;
  service: string;
}

export interface RunDiff {
  run1: {
    id: string;
    name: string;
    status: RunStatus;
    total_cost: number;
    total_tokens: number;
    span_count: number;
    start_time: string;
    end_time: string | null;
  };
  run2: {
    id: string;
    name: string;
    status: RunStatus;
    total_cost: number;
    total_tokens: number;
    span_count: number;
    start_time: string;
    end_time: string | null;
  };
  differences: {
    cost_diff: number;
    token_diff: number;
    span_count_diff: number;
    duration_diff: number;
  };
  spans: {
    only_in_run1: [string, SpanType][];
    only_in_run2: [string, SpanType][];
    common_count: number;
    differences: Array<{
      name: string;
      span_type: SpanType;
      duration_diff: number;
      cost_diff: number;
      status_changed: boolean;
      status_1: SpanStatus;
      status_2: SpanStatus;
    }>;
  };
}

export interface ReplayStep {
  id: string;
  name: string;
  span_type: SpanType;
  input_data: unknown;
  output_data: unknown;
  metadata: Record<string, unknown> | null;
  start_time: string;
  end_time: string | null;
  status: SpanStatus;
  error: string | null;
}

export interface ReplayData {
  run: {
    id: string;
    name: string;
    status: RunStatus;
    start_time: string;
    end_time: string | null;
    metadata: Record<string, unknown> | null;
  };
  steps: ReplayStep[];
  total_steps: number;
}

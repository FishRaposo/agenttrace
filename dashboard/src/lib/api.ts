/**
 * API client for communicating with the AgentTrace server.
 */

import type {
  Run,
  RunListResponse,
  TraceResponse,
  Stats,
  HealthResponse,
  RunDiff,
  ReplayData,
  CostSummary,
  CostTimeseries,
  ModelCostBreakdown,
  Budget,
  BudgetStatus,
} from "@/types";

const API_BASE_URL: string =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function fetchApi<T>(path: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE_URL}${path}`;
  const response = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
    ...options,
  });

  if (!response.ok) {
    throw new Error(`API error: ${response.status} ${response.statusText}`);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

export async function fetchRuns(
  limit: number = 20,
  offset: number = 0,
  correlationId?: string,
  status?: string,
  search?: string
): Promise<RunListResponse> {
  const params = new URLSearchParams({
    limit: String(limit),
    offset: String(offset),
  });
  if (correlationId) {
    params.set("correlation_id", correlationId);
  }
  if (status) {
    params.set("status", status);
  }
  if (search) {
    params.set("search", search);
  }
  return fetchApi<RunListResponse>(`/api/runs?${params.toString()}`);
}

export async function fetchRun(id: string): Promise<Run> {
  return fetchApi<Run>(`/api/runs/${id}`);
}

export async function fetchRunSpans(id: string): Promise<TraceResponse[]> {
  return fetchApi<TraceResponse[]>(`/api/runs/${id}/spans`);
}

export async function fetchStats(): Promise<Stats> {
  return fetchApi<Stats>("/api/stats");
}

export async function deleteRun(id: string): Promise<void> {
  await fetchApi<void>(`/api/runs/${id}`, { method: "DELETE" });
}

export async function healthCheck(): Promise<HealthResponse> {
  return fetchApi<HealthResponse>("/health");
}

export async function diffRuns(runId1: string, runId2: string): Promise<RunDiff> {
  return fetchApi<RunDiff>(`/api/diff/runs?run_id_1=${runId1}&run_id_2=${runId2}`);
}

export async function getReplayData(runId: string): Promise<ReplayData> {
  return fetchApi<ReplayData>(`/api/replay/runs/${runId}`);
}

// Cost analytics
export async function fetchCostSummary(): Promise<CostSummary> {
  return fetchApi<CostSummary>("/api/costs/summary");
}

export async function fetchCostTimeseries(
  granularity: string = "day",
  days: number = 30
): Promise<CostTimeseries> {
  return fetchApi<CostTimeseries>(`/api/costs/timeseries?granularity=${granularity}&days=${days}`);
}

export async function fetchCostByModel(): Promise<ModelCostBreakdown[]> {
  return fetchApi<ModelCostBreakdown[]>("/api/costs/by-model");
}

export async function fetchCostByProvider(): Promise<{ provider: string; total_cost: number; span_count: number }[]> {
  return fetchApi<{ provider: string; total_cost: number; span_count: number }[]>("/api/costs/by-provider");
}

export async function fetchCostByFeature(): Promise<{ feature: string; total_cost: number; span_count: number }[]> {
  return fetchApi<{ feature: string; total_cost: number; span_count: number }[]>("/api/costs/by-feature");
}

export async function fetchTopExpensiveRuns(limit: number = 10): Promise<{ id: string; name: string; total_cost: number; total_tokens: number; span_count: number; status: string; start_time: string }[]> {
  return fetchApi<{ id: string; name: string; total_cost: number; total_tokens: number; span_count: number; status: string; start_time: string }[]>(`/api/costs/top-runs?limit=${limit}`);
}

export async function fetchCostProjection(): Promise<{ trailing_7d_cost: number; trailing_30d_cost: number; daily_burn: number; monthly_projection: number }> {
  return fetchApi<{ trailing_7d_cost: number; trailing_30d_cost: number; daily_burn: number; monthly_projection: number }>("/api/costs/projection");
}

// Budgets
export async function fetchBudgets(): Promise<Budget[]> {
  return fetchApi<Budget[]>("/api/budgets");
}

export async function fetchBudgetStatus(budgetId: string): Promise<BudgetStatus> {
  return fetchApi<BudgetStatus>(`/api/budgets/${budgetId}/status`);
}

// Live tail (SSE)
export function streamTraces(callback: (trace: TraceResponse) => void): () => void {
  const url = `${API_BASE_URL}/api/stream/traces`;
  const eventSource = new EventSource(url);

  eventSource.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      callback(data as TraceResponse);
    } catch {
      // ignore parse errors
    }
  };

  eventSource.onerror = () => {
    eventSource.close();
  };

  return () => eventSource.close();
}

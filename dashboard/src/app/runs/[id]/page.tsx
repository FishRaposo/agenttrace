"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import type { Run, TraceResponse, RunStatus } from "@/types";
import { fetchRun, fetchRunSpans } from "@/lib/api";
import { RunTimeline } from "@/components/RunTimeline";
import { SpanDetail } from "@/components/SpanDetail";
import { CostBreakdown } from "@/components/CostBreakdown";
import { TokenUsage } from "@/components/TokenUsage";
import { RunDiff } from "@/components/RunDiff";
import { PromptReplay } from "@/components/PromptReplay";
import { fetchRuns } from "@/lib/api";

function StatusBadge({ status }: { status: RunStatus }): JSX.Element {
  const classes: Record<RunStatus, string> = {
    completed: "status-completed",
    running: "status-running",
    failed: "status-failed",
    cancelled: "status-cancelled",
  };

  return <span className={`status-badge ${classes[status]}`}>{status}</span>;
}

function formatCost(cost: number): string {
  return `$${cost.toFixed(4)}`;
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleString();
}

export default function RunDetailPage(): JSX.Element {
  const params = useParams<{ id: string }>();
  const runId = params.id;

  const [run, setRun] = useState<Run | null>(null);
  const [spans, setSpans] = useState<TraceResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"spans" | "compare" | "replay">("spans");
  const [compareRunId, setCompareRunId] = useState<string>("");
  const [otherRuns, setOtherRuns] = useState<Run[]>([]);
  const [loadingOtherRuns, setLoadingOtherRuns] = useState(false);

  useEffect(() => {
    if (!runId) return;

    async function loadRunData() {
      setLoading(true);
      setError(null);
      try {
        const [runData, spanData] = await Promise.all([
          fetchRun(runId),
          fetchRunSpans(runId),
        ]);
        setRun(runData);
        setSpans(spanData);
      } catch (err) {
        const message = err instanceof Error ? err.message : "Failed to load run data";
        setError(message.includes("404") ? "Run not found" : message);
      } finally {
        setLoading(false);
      }
    }

    loadRunData();
  }, [runId]);

  useEffect(() => {
    if (activeTab !== "compare" || !runId) return;
    async function loadOtherRuns() {
      setLoadingOtherRuns(true);
      try {
        const data = await fetchRuns(50);
        setOtherRuns(data.runs.filter((r) => r.id !== runId));
      } catch {
        setOtherRuns([]);
      } finally {
        setLoadingOtherRuns(false);
      }
    }
    loadOtherRuns();
  }, [activeTab, runId]);

  if (loading) {
    return (
      <div className="text-center py-16">
        <p className="text-gray-500">Loading run...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-16">
        <p className="text-gray-500">{error}</p>
      </div>
    );
  }

  if (!run) {
    return (
      <div className="text-center py-16">
        <p className="text-gray-500">Run not found.</p>
      </div>
    );
  }

  return (
    <div>
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-2">
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white">{run.name}</h2>
          <StatusBadge status={run.status} />
        </div>
        <div className="flex gap-6 text-sm text-gray-500 flex-wrap">
          <span>Started: {formatDate(run.start_time)}</span>
          {run.end_time && <span>Ended: {formatDate(run.end_time)}</span>}
          <span>Cost: {formatCost(run.total_cost)}</span>
          <span>Tokens: {run.total_tokens.toLocaleString()}</span>
          <span>Spans: {run.span_count}</span>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <RunTimeline spans={spans} />
        </div>
        <div className="space-y-6">
          <CostBreakdown spans={spans} />
          <TokenUsage spans={spans} />
        </div>
      </div>

      <div className="mt-6">
        <div className="border-b border-gray-200 mb-6">
          <nav className="flex gap-4">
            {(["spans", "compare", "replay"] as const).map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                  activeTab === tab
                    ? "border-trace-600 text-trace-700"
                    : "border-transparent text-gray-500 hover:text-gray-700"
                }`}
              >
                {tab === "spans" ? "Spans" : tab === "compare" ? "Compare" : "Replay"}
              </button>
            ))}
          </nav>
        </div>

        {activeTab === "spans" && <SpanDetail spans={spans} />}

        {activeTab === "compare" && (
          <div>
            <div className="mb-6">
              <label className="text-sm text-gray-500 mr-2">Compare with:</label>
              <select
                value={compareRunId}
                onChange={(e) => setCompareRunId(e.target.value)}
                className="border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 rounded-md px-3 py-1.5 text-sm"
              >
                <option value="">Select a run...</option>
                {otherRuns.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.name} ({r.id.slice(0, 8)}...)
                  </option>
                ))}
              </select>
              {loadingOtherRuns && (
                <span className="ml-2 text-gray-400 text-sm">Loading...</span>
              )}
            </div>
            {compareRunId && <RunDiff runId1={runId} runId2={compareRunId} />}
          </div>
        )}

        {activeTab === "replay" && <PromptReplay runId={runId} />}
      </div>
    </div>
  );
}

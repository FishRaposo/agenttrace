"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { GitCompare, Play, X } from "lucide-react";
import type { Run, TraceResponse, RunStatus } from "@/types";
import { fetchRun, fetchRunSpans, fetchRuns } from "@/lib/api";
import { DEMO_COMPARE_TARGET_ID } from "@/lib/demoData";
import { RunTimeline } from "@/components/RunTimeline";
import { SpanDetail } from "@/components/SpanDetail";
import { CostBreakdown } from "@/components/CostBreakdown";
import { TokenUsage } from "@/components/TokenUsage";
import { RunDiff } from "@/components/RunDiff";
import { PromptReplay } from "@/components/PromptReplay";

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
  const [compareRunId, setCompareRunId] = useState<string>(DEMO_COMPARE_TARGET_ID);
  const [otherRuns, setOtherRuns] = useState<Run[]>([]);
  const [loadingOtherRuns, setLoadingOtherRuns] = useState(false);
  const [showReplayPanel, setShowReplayPanel] = useState(false);
  const [showDiffPanel, setShowDiffPanel] = useState(false);

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

  const defaultCompareId =
    runId === DEMO_COMPARE_TARGET_ID ? "demo-run-005" : DEMO_COMPARE_TARGET_ID;
  const diffCompareId = compareRunId || defaultCompareId;

  return (
    <div>
      <div className="mb-8">
        <div className="flex flex-wrap items-start justify-between gap-4 mb-2">
          <div className="flex items-center gap-3">
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white">{run.name}</h2>
            <StatusBadge status={run.status} />
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              data-testid="run-replay-action"
              onClick={() => {
                setShowReplayPanel(true);
                setActiveTab("replay");
              }}
              className="inline-flex items-center gap-2 rounded-lg bg-trace-600 px-4 py-2 text-sm font-medium text-white hover:bg-trace-700 transition-colors"
            >
              <Play className="h-4 w-4" />
              Replay
            </button>
            <button
              type="button"
              data-testid="run-diff-action"
              onClick={() => {
                if (!compareRunId) setCompareRunId(defaultCompareId);
                setShowDiffPanel(true);
                setActiveTab("compare");
              }}
              className="inline-flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-900 hover:bg-gray-50 dark:border-gray-700 dark:bg-gray-900 dark:text-white dark:hover:bg-gray-800 transition-colors"
            >
              <GitCompare className="h-4 w-4" />
              Diff
            </button>
          </div>
        </div>
        <div className="flex gap-6 text-sm text-gray-500 flex-wrap">
          <span>Started: {formatDate(run.start_time)}</span>
          {run.end_time && <span>Ended: {formatDate(run.end_time)}</span>}
          <span>Cost: {formatCost(run.total_cost)}</span>
          <span>Tokens: {run.total_tokens.toLocaleString()}</span>
          <span>Spans: {run.span_count}</span>
          {run.metadata?.workflow === "issue_pr" && (
            <span className="text-amber-700 dark:text-amber-300">
              Issue-to-PR trace — draft-only, no GitHub call
            </span>
          )}
        </div>
      </div>

      {showReplayPanel && (
        <div
          className="fixed inset-0 z-50 flex items-start justify-center bg-black/40 p-4 sm:p-8"
          role="dialog"
          aria-label="Replay panel"
          data-testid="run-replay-panel"
        >
          <div className="w-full max-w-5xl max-h-[90vh] overflow-y-auto rounded-xl bg-white dark:bg-gray-950 shadow-xl">
            <div className="sticky top-0 flex items-center justify-between border-b border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-950 px-4 py-3">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Replay</h3>
              <button
                type="button"
                onClick={() => setShowReplayPanel(false)}
                className="rounded-lg p-2 text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800"
                aria-label="Close replay panel"
              >
                <X className="h-5 w-5" />
              </button>
            </div>
            <div className="p-4">
              <PromptReplay runId={runId} />
            </div>
          </div>
        </div>
      )}

      {showDiffPanel && (
        <div
          className="fixed inset-0 z-50 flex items-start justify-center bg-black/40 p-4 sm:p-8"
          role="dialog"
          aria-label="Diff panel"
          data-testid="run-diff-panel"
        >
          <div className="w-full max-w-5xl max-h-[90vh] overflow-y-auto rounded-xl bg-white dark:bg-gray-950 shadow-xl">
            <div className="sticky top-0 flex items-center justify-between border-b border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-950 px-4 py-3">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Run diff</h3>
              <button
                type="button"
                onClick={() => setShowDiffPanel(false)}
                className="rounded-lg p-2 text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800"
                aria-label="Close diff panel"
              >
                <X className="h-5 w-5" />
              </button>
            </div>
            <div className="p-4">
              <RunDiff runId1={runId} runId2={diffCompareId} />
            </div>
          </div>
        </div>
      )}

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

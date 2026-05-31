"use client";

import { useEffect, useState } from "react";
import { diffRuns } from "@/lib/api";
import type { RunDiff, SpanType, SpanStatus } from "@/types";

interface RunDiffProps {
  runId1: string;
  runId2: string;
}

function formatCost(cost: number): string {
  return `$${cost.toFixed(4)}`;
}

function formatDuration(seconds: number): string {
  if (seconds < 60) return `${seconds.toFixed(1)}s`;
  return `${(seconds / 60).toFixed(1)}m`;
}

function formatDiff(value: number): string {
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(4)}`;
}

function getSpanTypeLabel(type: SpanType): string {
  const labels: Record<SpanType, string> = {
    llm_call: "LLM Call",
    tool_call: "Tool Call",
    decision: "Decision",
    retrieval: "Retrieval",
    custom: "Custom",
  };
  return labels[type];
}

export function RunDiff({ runId1, runId2 }: RunDiffProps): JSX.Element {
  const [diff, setDiff] = useState<RunDiff | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadDiff() {
      setLoading(true);
      setError(null);
      try {
        const data = await diffRuns(runId1, runId2);
        setDiff(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load diff");
      } finally {
        setLoading(false);
      }
    }
    loadDiff();
  }, [runId1, runId2]);

  if (loading) {
    return (
      <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-6">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
          Run Comparison
        </h3>
        <p className="text-gray-400 text-sm">Loading comparison...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-6">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
          Run Comparison
        </h3>
        <p className="text-red-500 text-sm">{error}</p>
      </div>
    );
  }

  if (!diff) {
    return <div className="text-gray-400 text-sm">No comparison data available.</div>;
  }

  return (
    <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-6">
      <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
        Run Comparison
      </h3>

      <div className="grid grid-cols-2 gap-4 mb-6">
        <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
          <h4 className="font-medium text-gray-900 dark:text-white mb-2">
            {diff.run1.name}
          </h4>
          <div className="space-y-1 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-500">Cost:</span>
              <span className="font-medium">{formatCost(diff.run1.total_cost)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">Tokens:</span>
              <span className="font-medium">{diff.run1.total_tokens.toLocaleString()}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">Spans:</span>
              <span className="font-medium">{diff.run1.span_count}</span>
            </div>
          </div>
        </div>
        <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
          <h4 className="font-medium text-gray-900 dark:text-white mb-2">
            {diff.run2.name}
          </h4>
          <div className="space-y-1 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-500">Cost:</span>
              <span className="font-medium">{formatCost(diff.run2.total_cost)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">Tokens:</span>
              <span className="font-medium">{diff.run2.total_tokens.toLocaleString()}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">Spans:</span>
              <span className="font-medium">{diff.run2.span_count}</span>
            </div>
          </div>
        </div>
      </div>

      <div className="border-t border-gray-200 dark:border-gray-700 pt-4 mb-6">
        <h4 className="font-medium text-gray-900 dark:text-white mb-3">Differences</h4>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
          <div>
            <span className="text-gray-500">Cost Diff:</span>
            <p className={`font-medium ${diff.differences.cost_diff > 0 ? "text-red-500" : diff.differences.cost_diff < 0 ? "text-green-500" : "text-gray-900"}`}>
              {formatDiff(diff.differences.cost_diff)}
            </p>
          </div>
          <div>
            <span className="text-gray-500">Token Diff:</span>
            <p className={`font-medium ${diff.differences.token_diff > 0 ? "text-red-500" : diff.differences.token_diff < 0 ? "text-green-500" : "text-gray-900"}`}>
              {formatDiff(diff.differences.token_diff)}
            </p>
          </div>
          <div>
            <span className="text-gray-500">Span Count Diff:</span>
            <p className={`font-medium ${diff.differences.span_count_diff > 0 ? "text-red-500" : diff.differences.span_count_diff < 0 ? "text-green-500" : "text-gray-900"}`}>
              {formatDiff(diff.differences.span_count_diff)}
            </p>
          </div>
          <div>
            <span className="text-gray-500">Duration Diff:</span>
            <p className={`font-medium ${diff.differences.duration_diff > 0 ? "text-red-500" : diff.differences.duration_diff < 0 ? "text-green-500" : "text-gray-900"}`}>
              {formatDuration(diff.differences.duration_diff)}
            </p>
          </div>
        </div>
      </div>

      <div className="border-t border-gray-200 dark:border-gray-700 pt-4">
        <h4 className="font-medium text-gray-900 dark:text-white mb-3">Span Differences</h4>
        
        {diff.spans.only_in_run1.length > 0 && (
          <div className="mb-4">
            <p className="text-sm text-gray-500 mb-2">Only in {diff.run1.name}:</p>
            <div className="flex flex-wrap gap-2">
              {diff.spans.only_in_run1.map(([name, type]) => (
                <span
                  key={`${name}-${type}`}
                  className="px-2 py-1 bg-red-100 dark:bg-red-900 text-red-800 dark:text-red-200 rounded text-xs"
                >
                  {name} ({getSpanTypeLabel(type)})
                </span>
              ))}
            </div>
          </div>
        )}

        {diff.spans.only_in_run2.length > 0 && (
          <div className="mb-4">
            <p className="text-sm text-gray-500 mb-2">Only in {diff.run2.name}:</p>
            <div className="flex flex-wrap gap-2">
              {diff.spans.only_in_run2.map(([name, type]) => (
                <span
                  key={`${name}-${type}`}
                  className="px-2 py-1 bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-200 rounded text-xs"
                >
                  {name} ({getSpanTypeLabel(type)})
                </span>
              ))}
            </div>
          </div>
        )}

        {diff.spans.differences.length > 0 && (
          <div>
            <p className="text-sm text-gray-500 mb-2">Changed spans:</p>
            <div className="space-y-2">
              {diff.spans.differences.map((spanDiff) => (
                <div
                  key={spanDiff.name}
                  className="bg-gray-50 dark:bg-gray-800 rounded p-3 text-sm"
                >
                  <div className="flex justify-between items-center mb-1">
                    <span className="font-medium">{spanDiff.name}</span>
                    <span className="text-xs text-gray-500">{getSpanTypeLabel(spanDiff.span_type)}</span>
                  </div>
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <div>
                      <span className="text-gray-500">Duration:</span>
                      <span className={`ml-1 ${spanDiff.duration_diff > 0 ? "text-red-500" : spanDiff.duration_diff < 0 ? "text-green-500" : ""}`}>
                        {formatDiff(spanDiff.duration_diff)}ms
                      </span>
                    </div>
                    <div>
                      <span className="text-gray-500">Cost:</span>
                      <span className={`ml-1 ${spanDiff.cost_diff > 0 ? "text-red-500" : spanDiff.cost_diff < 0 ? "text-green-500" : ""}`}>
                        {formatDiff(spanDiff.cost_diff)}
                      </span>
                    </div>
                  </div>
                  {spanDiff.status_changed && (
                    <div className="mt-1 text-xs">
                      <span className="text-gray-500">Status:</span>
                      <span className="ml-1">{spanDiff.status_1}</span>
                      <span className="mx-1">→</span>
                      <span className={spanDiff.status_2 === "error" ? "text-red-500" : ""}>{spanDiff.status_2}</span>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {diff.spans.only_in_run1.length === 0 &&
         diff.spans.only_in_run2.length === 0 &&
         diff.spans.differences.length === 0 && (
          <p className="text-gray-400 text-sm">No span differences found.</p>
        )}
      </div>
    </div>
  );
}

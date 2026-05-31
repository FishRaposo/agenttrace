"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { Search } from "lucide-react";
import { fetchRuns, deleteRun } from "@/lib/api";
import type { Run, RunStatus } from "@/types";

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleString();
}

function formatCost(cost: number): string {
  return `$${cost.toFixed(4)}`;
}

function StatusBadge({ status }: { status: RunStatus }): JSX.Element {
  const classes: Record<RunStatus, string> = {
    completed: "status-completed",
    running: "status-running",
    failed: "status-failed",
    cancelled: "status-cancelled",
  };

  return <span className={`status-badge ${classes[status]}`}>{status}</span>;
}

export default function RunsPage(): JSX.Element {
  const [runs, setRuns] = useState<Run[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [searchQuery, setSearchQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const limit = 20;

  const loadRuns = useCallback(
    async (pageOffset: number, status: string, search: string) => {
      setLoading(true);
      setError(null);
      try {
        const data = await fetchRuns(
          limit,
          pageOffset,
          undefined,
          status || undefined,
          search || undefined
        );
        setRuns(data.runs);
        setTotal(data.total);
      } catch (err) {
        setError(
          err instanceof Error ? err.message : "Failed to load runs"
        );
      } finally {
        setLoading(false);
      }
    },
    []
  );

  useEffect(() => {
    loadRuns(offset, statusFilter, searchQuery);
  }, [offset, statusFilter, searchQuery, loadRuns]);

  const totalPages = Math.ceil(total / limit);
  const currentPage = Math.floor(offset / limit) + 1;

  async function handleDelete(runId: string) {
    try {
      await deleteRun(runId);
      setDeleteError(null);
      loadRuns(offset, statusFilter, searchQuery);
    } catch (err) {
      setDeleteError(err instanceof Error ? err.message : "Failed to delete run");
    }
  }

  function handleStatusChange(status: string) {
    setStatusFilter(status);
    setOffset(0);
  }

  function handleSearch(value: string) {
    setSearchQuery(value);
    setOffset(0);
  }

  return (
    <div>
      <div className="mb-8">
        <h2 className="text-2xl font-bold text-gray-900">Runs</h2>
        <p className="text-gray-500 mt-1">
          View and inspect all agent runs.
        </p>
      </div>

      <div className="mb-4 flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
          <input
            type="text"
            placeholder="Search runs..."
            value={searchQuery}
            onChange={(e) => handleSearch(e.target.value)}
            className="w-full pl-9 pr-4 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-trace-500 focus:border-transparent"
          />
        </div>
        <div className="flex gap-1 flex-wrap">
          {["", "completed", "running", "failed", "cancelled"].map((s) => (
            <button
              key={s}
              onClick={() => handleStatusChange(s)}
              className={`px-3 py-1 rounded-md text-sm font-medium transition-colors ${
                statusFilter === s
                  ? "bg-trace-600 text-white"
                  : "bg-gray-100 text-gray-600 hover:bg-gray-200"
              }`}
            >
              {s || "All"}
            </button>
          ))}
        </div>
      </div>

      {deleteError && (
        <div className="mb-4 bg-red-50 border border-red-200 rounded-lg p-3 flex items-center justify-between">
          <p className="text-red-700 text-sm">{deleteError}</p>
          <button
            onClick={() => setDeleteError(null)}
            className="text-xs text-red-500 hover:text-red-700"
          >
            Dismiss
          </button>
        </div>
      )}

      {error ? (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6">
          <p className="text-yellow-700 text-sm">
            Failed to load runs: {error}
          </p>
          <button
            onClick={() => loadRuns(offset, statusFilter, searchQuery)}
            className="mt-3 text-sm text-trace-600 hover:underline"
          >
            Retry
          </button>
        </div>
      ) : (
        <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-200 bg-gray-50">
                <th className="py-3 px-4 text-left text-xs font-semibold text-gray-500 uppercase">
                  Name
                </th>
                <th className="py-3 px-4 text-left text-xs font-semibold text-gray-500 uppercase">
                  Status
                </th>
                <th className="py-3 px-4 text-left text-xs font-semibold text-gray-500 uppercase">
                  Started
                </th>
                <th className="py-3 px-4 text-left text-xs font-semibold text-gray-500 uppercase">
                  Cost
                </th>
                <th className="py-3 px-4 text-left text-xs font-semibold text-gray-500 uppercase">
                  Tokens
                </th>
                  <th className="py-3 px-4 text-left text-xs font-semibold text-gray-500 uppercase">
                    Spans
                  </th>
                  <th className="py-3 px-4 text-left text-xs font-semibold text-gray-500 uppercase">
                    Correlation
                  </th>
                  <th className="py-3 px-4 text-right text-xs font-semibold text-gray-500 uppercase">
                    Actions
                  </th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td
                    colSpan={8}
                    className="py-8 text-center text-gray-400"
                  >
                    Loading...
                  </td>
                </tr>
              ) : runs.length === 0 ? (
                <tr>
                  <td
                    colSpan={8}
                    className="py-8 text-center text-gray-400"
                  >
                    {searchQuery || statusFilter
                      ? "No runs match your filters."
                      : "No runs found. Run an agent with AgentTrace to see traces here."}
                  </td>
                </tr>
              ) : (
                runs.map((run) => (
                  <tr
                    key={run.id}
                    className="border-b border-gray-100 hover:bg-gray-50"
                  >
                    <td className="py-3 px-4">
                      <Link
                        href={`/runs/${run.id}`}
                        className="text-trace-700 hover:underline font-medium"
                      >
                        {run.name}
                      </Link>
                    </td>
                    <td className="py-3 px-4">
                      <StatusBadge status={run.status} />
                    </td>
                    <td className="py-3 px-4 text-sm text-gray-600">
                      {formatDate(run.start_time)}
                    </td>
                    <td className="py-3 px-4 text-sm text-gray-600">
                      {formatCost(run.total_cost)}
                    </td>
                    <td className="py-3 px-4 text-sm text-gray-600">
                      {run.total_tokens.toLocaleString()}
                    </td>
                    <td className="py-3 px-4 text-sm text-gray-600">
                      {run.span_count}
                    </td>
                    <td className="py-3 px-4 text-sm text-gray-500 font-mono">
                      {run.correlation_id
                        ? run.correlation_id.slice(0, 8) + "..."
                        : "—"}
                    </td>
                    <td className="py-3 px-4 text-right">
                      <button
                        onClick={() => handleDelete(run.id)}
                        className="text-red-500 hover:text-red-700 text-sm"
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>

          {total > limit && (
            <div className="flex items-center justify-between px-4 py-3 border-t border-gray-100 bg-gray-50">
              <span className="text-sm text-gray-500">
                Showing {(currentPage - 1) * limit + 1}–
                {Math.min(currentPage * limit, total)} of {total}
              </span>
              <div className="flex gap-2">
                <button
                  onClick={() => setOffset(Math.max(0, offset - limit))}
                  disabled={offset === 0}
                  className="px-3 py-1 text-sm rounded bg-white border border-gray-200 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
                >
                  Previous
                </button>
                <button
                  onClick={() => setOffset(offset + limit)}
                  disabled={offset + limit >= total}
                  className="px-3 py-1 text-sm rounded bg-white border border-gray-200 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

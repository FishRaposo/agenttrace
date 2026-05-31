"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Activity, DollarSign, Clock, Zap } from "lucide-react";
import { fetchStats, fetchRuns } from "@/lib/api";
import type { Stats, Run } from "@/types";

interface StatCardProps {
  title: string;
  value: string;
  icon: React.ReactNode;
  subtitle: string;
}

function StatCard({ title, value, icon, subtitle }: StatCardProps): JSX.Element {
  return (
    <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-6">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-gray-500">{title}</p>
          <p className="text-2xl font-bold text-gray-900 mt-1">{value}</p>
          <p className="text-xs text-gray-400 mt-1">{subtitle}</p>
        </div>
        <div className="p-3 bg-trace-50 rounded-lg">{icon}</div>
      </div>
    </div>
  );
}

function formatCost(cost: number): string {
  return `$${cost.toFixed(4)}`;
}

function formatDuration(ms: number): string {
  if (ms < 1000) return `${Math.round(ms)}ms`;
  return `${(ms / 1000).toFixed(2)}s`;
}

function formatTokens(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return n.toLocaleString();
}

function StatusBadge({ status }: { status: string }): JSX.Element {
  const classes: Record<string, string> = {
    completed: "status-completed",
    running: "status-running",
    failed: "status-failed",
    cancelled: "status-cancelled",
  };

  return <span className={`status-badge ${classes[status] ?? ""}`}>{status}</span>;
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleString();
}

export default function HomePage(): JSX.Element {
  const [stats, setStats] = useState<Stats | null>(null);
  const [recentRuns, setRecentRuns] = useState<Run[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadData() {
      try {
        const [statsData, runsData] = await Promise.all([
          fetchStats(),
          fetchRuns(5, 0),
        ]);
        setStats(statsData);
        setRecentRuns(runsData.runs);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load data");
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  if (error) {
    return (
      <div>
        <div className="mb-8">
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white">Dashboard</h2>
          <p className="text-gray-500 dark:text-gray-400 mt-1">
            Monitor your agent runs, costs, and performance.
          </p>
        </div>
        <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-6">
          <p className="text-yellow-700 dark:text-yellow-300 text-sm">
            Could not connect to the trace server. Make sure it&apos;s running at{" "}
            <code className="bg-yellow-100 px-1 rounded">
              {process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}
            </code>
          </p>
        </div>
      </div>
    );
  }

  return (
    <div>
      <div className="mb-8">
        <h2 className="text-2xl font-bold text-gray-900">Dashboard</h2>
        <p className="text-gray-500 mt-1">
          Monitor your agent runs, costs, and performance.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <StatCard
          title="Total Runs"
          value={loading ? "—" : String(stats?.total_runs ?? 0)}
          icon={<Activity className="h-6 w-6 text-trace-600" />}
          subtitle="All time"
        />
        <StatCard
          title="Total Cost"
          value={loading ? "—" : formatCost(stats?.total_cost ?? 0)}
          icon={<DollarSign className="h-6 w-6 text-trace-600" />}
          subtitle="Accumulated"
        />
        <StatCard
          title="Avg Latency"
          value={loading ? "—" : formatDuration(stats?.avg_duration_ms ?? 0)}
          icon={<Clock className="h-6 w-6 text-trace-600" />}
          subtitle="Per span"
        />
        <StatCard
          title="Total Tokens"
          value={loading ? "—" : formatTokens(stats?.total_tokens ?? 0)}
          icon={<Zap className="h-6 w-6 text-trace-600" />}
          subtitle="All runs"
        />
      </div>

      <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">
          Recent Runs
        </h3>

        {loading ? (
          <p className="text-gray-400 text-sm">Loading...</p>
        ) : recentRuns.length === 0 ? (
          <p className="text-gray-500 text-sm">
            No runs recorded yet.{" "}
            <Link href="/runs" className="text-trace-600 hover:underline">
              View all runs →
            </Link>
          </p>
        ) : (
          <div>
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
                </tr>
              </thead>
              <tbody>
                {recentRuns.map((run) => (
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
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="mt-4">
              <Link
                href="/runs"
                className="text-trace-600 hover:underline text-sm"
              >
                View all runs →
              </Link>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

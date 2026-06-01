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
  accentClass: string;
}

function StatCard({ title, value, icon, subtitle, accentClass }: StatCardProps): JSX.Element {
  return (
    <div className="relative overflow-hidden rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-slate-900/60 p-6 shadow-md backdrop-blur-sm transition-all hover:-translate-y-1 hover:shadow-lg">
      <div className={`absolute top-0 left-0 right-0 h-[2px] ${accentClass}`} />
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-gray-400 dark:text-slate-500">{title}</p>
          <p className="text-2xl font-bold text-gray-900 dark:text-white mt-2">{value}</p>
          <p className="text-xs text-gray-400 mt-1">{subtitle}</p>
        </div>
        <div className="p-3 bg-slate-50 dark:bg-slate-800/40 rounded-lg">{icon}</div>
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
    completed: "bg-emerald-100 text-emerald-800 dark:bg-emerald-950/30 dark:text-emerald-400 border border-emerald-500/10",
    running: "bg-blue-100 text-blue-800 dark:bg-blue-950/30 dark:text-blue-400 border border-blue-500/10 animate-pulse",
    failed: "bg-rose-100 text-rose-800 dark:bg-rose-950/30 dark:text-rose-400 border border-rose-500/10",
    cancelled: "bg-gray-100 text-gray-800 dark:bg-slate-850 dark:text-slate-400 border border-slate-700/20",
  };

  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold tracking-wide ${classes[status] ?? ""}`}>
      {status}
    </span>
  );
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
      <div className="max-w-6xl mx-auto px-4 py-8">
        <div className="mb-8">
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white">Dashboard</h2>
          <p className="text-gray-500 dark:text-gray-400 mt-1">
            Monitor your agent runs, costs, and performance.
          </p>
        </div>
        <div className="bg-rose-50 dark:bg-rose-900/10 border border-rose-200 dark:border-rose-800/30 rounded-xl p-6 shadow-md">
          <h3 className="font-bold text-rose-800 dark:text-rose-400 text-lg mb-2">Observability Service Offline</h3>
          <p className="text-rose-700 dark:text-rose-450 text-sm">
            Could not connect to the trace server. Make sure the backend endpoint is running at{" "}
            <code className="bg-rose-100 dark:bg-rose-950 px-1.5 py-0.5 rounded font-mono text-xs">
              {process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}
            </code>
          </p>
        </div>
      </div>
    );
  }

  // Calculate dur points for SVG dur timeline
  const latencyPoints = recentRuns.slice(0, 5).reverse().map((r) => r.span_count);
  const chartHeight = 40;
  const chartWidth = 480;
  const maxSpan = latencyPoints.length > 0 ? Math.max(...latencyPoints, 5) : 10;
  const pointsStr = latencyPoints
    .map((spans, idx) => {
      const x = (idx / Math.max(latencyPoints.length - 1, 1)) * chartWidth;
      const y = chartHeight - (spans / maxSpan) * chartHeight * 0.8 - 4;
      return `${x},${y}`;
    })
    .join(" ");

  return (
    <div className="max-w-6xl mx-auto px-4 py-8 text-slate-100">
      {/* Hero Banner Header with premium gradient */}
      <div className="relative mb-8 overflow-hidden rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/60 p-8 shadow-xl backdrop-blur-md">
        <div className="absolute right-0 top-0 h-40 w-40 rounded-full bg-violet-500/5 blur-3xl" />
        <div className="absolute left-1/3 bottom-0 h-40 w-40 rounded-full bg-sky-500/5 blur-3xl" />
        <div className="relative">
          <h1 className="text-3xl font-extrabold tracking-tight text-gray-900 dark:bg-gradient-to-r dark:from-slate-100 dark:via-slate-200 dark:to-sky-400 dark:bg-clip-text dark:text-transparent">
            AgentTrace Panel
          </h1>
          <p className="text-slate-400 mt-2 text-sm max-w-xl">
            Monitor real-time distributed spans, track granular model token pricing, and audit LLM FinOps budgets across agent runs.
          </p>
        </div>
      </div>

      {/* KPI Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <StatCard
          title="Total Runs"
          value={loading ? "—" : String(stats?.total_runs ?? 0)}
          icon={<Activity className="h-6 w-6 text-sky-500" />}
          subtitle="Buffer history length"
          accentClass="bg-sky-500"
        />
        <StatCard
          title="Total Spending"
          value={loading ? "—" : formatCost(stats?.total_cost ?? 0)}
          icon={<DollarSign className="h-6 w-6 text-emerald-500" />}
          subtitle="Model invocation cost"
          accentClass="bg-emerald-500"
        />
        <StatCard
          title="Avg Latency"
          value={loading ? "—" : formatDuration(stats?.avg_duration_ms ?? 0)}
          icon={<Clock className="h-6 w-6 text-amber-500" />}
          subtitle="Average span execution time"
          accentClass="bg-amber-500"
        />
        <StatCard
          title="Total Tokens"
          value={loading ? "—" : formatTokens(stats?.total_tokens ?? 0)}
          icon={<Zap className="h-6 w-6 text-violet-500" />}
          subtitle="Accumulated token count"
          accentClass="bg-violet-500"
        />
      </div>

      {/* Observability Visual Trend */}
      <section className="mb-8 rounded-xl border border-gray-200 dark:border-slate-800 bg-white dark:bg-slate-900/40 p-6 shadow-md backdrop-blur-sm">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-sm font-bold text-gray-900 dark:text-slate-200">Operation Volume Trajectory</h2>
            <p className="text-xs text-gray-400 dark:text-slate-500">Span complexity metrics across recent agent runs</p>
          </div>
          <span className="text-xs font-semibold text-sky-400">Live Telemetry Active</span>
        </div>
        <div className="h-10 flex items-end">
          {latencyPoints.length === 0 ? (
            <div className="w-full text-center text-xs text-slate-600">No active runs recorded</div>
          ) : (
            <svg width="100%" height={chartHeight} viewBox={`0 0 ${chartWidth} ${chartHeight}`} preserveAspectRatio="none" className="overflow-visible">
              <polyline
                fill="none"
                stroke="#38bdf8"
                strokeWidth="2.5"
                strokeLinecap="round"
                strokeLinejoin="round"
                points={pointsStr}
                className="drop-shadow-[0_2px_4px_rgba(56,189,248,0.3)]"
              />
            </svg>
          )}
        </div>
      </section>

      {/* Recent Runs Table Container */}
      <div className="bg-white dark:bg-slate-900/60 rounded-xl border border-gray-200 dark:border-slate-800 p-6 shadow-lg backdrop-blur-sm">
        <div className="flex justify-between items-center mb-6">
          <h3 className="text-lg font-bold text-gray-900 dark:text-slate-100">
            Recent Agent Runs
          </h3>
          <Link
            href="/runs"
            className="text-xs font-bold text-sky-500 hover:text-sky-400 transition-colors"
          >
            Browse All Runs →
          </Link>
        </div>

        {loading ? (
          <div className="flex justify-center py-8">
            <div className="h-6 w-6 animate-spin rounded-full border-2 border-sky-400 border-t-transparent" />
          </div>
        ) : recentRuns.length === 0 ? (
          <p className="text-gray-500 dark:text-slate-500 text-sm py-8 text-center border border-dashed border-gray-200 dark:border-slate-800 rounded-lg">
            No runs recorded yet. Deploy an agent SDK tracer wrapper to start capturing logs.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-gray-200 dark:border-slate-800/80 bg-gray-50 dark:bg-slate-950/20 text-gray-500 dark:text-slate-400">
                  <th className="py-3 px-4 font-semibold uppercase tracking-wider">Name</th>
                  <th className="py-3 px-4 font-semibold uppercase tracking-wider">Status</th>
                  <th className="py-3 px-4 font-semibold uppercase tracking-wider">Started</th>
                  <th className="py-3 px-4 font-semibold uppercase tracking-wider">Cost</th>
                  <th className="py-3 px-4 font-semibold uppercase tracking-wider">Tokens</th>
                  <th className="py-3 px-4 font-semibold uppercase tracking-wider">Spans</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 dark:divide-slate-800/60">
                {recentRuns.map((run) => (
                  <tr
                    key={run.id}
                    className="hover:bg-gray-50 dark:hover:bg-slate-800/20 transition-colors"
                  >
                    <td className="py-3.5 px-4 font-semibold text-gray-900 dark:text-slate-200">
                      <Link
                        href={`/runs/${run.id}`}
                        className="text-sky-600 dark:text-sky-400 hover:underline font-semibold"
                      >
                        {run.name}
                      </Link>
                    </td>
                    <td className="py-3.5 px-4">
                      <StatusBadge status={run.status} />
                    </td>
                    <td className="py-3.5 px-4 text-gray-600 dark:text-slate-450">
                      {formatDate(run.start_time)}
                    </td>
                    <td className="py-3.5 px-4 font-medium text-emerald-600 dark:text-emerald-400">
                      {formatCost(run.total_cost)}
                    </td>
                    <td className="py-3.5 px-4 text-gray-600 dark:text-slate-450 font-medium">
                      {run.total_tokens.toLocaleString()}
                    </td>
                    <td className="py-3.5 px-4 text-gray-600 dark:text-slate-450 font-medium">
                      {run.span_count}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

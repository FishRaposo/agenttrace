"use client";

import { useEffect, useState } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  LineChart,
  Line,
  CartesianGrid,
} from "recharts";
import { DollarSign, Coins, BarChart3, TrendingUp } from "lucide-react";
import {
  fetchCostSummary,
  fetchCostTimeseries,
  fetchCostByModel,
  fetchCostByProvider,
  fetchCostByFeature,
  fetchTopExpensiveRuns,
  fetchCostProjection,
  fetchBudgets,
  fetchBudgetStatus,
  fetchDailyCostReport,
} from "@/lib/api";
import type { CostSummary, ModelCostBreakdown, Budget, BudgetStatus, DailyCostReport } from "@/types";

const COLORS = ["#10b981", "#3b82f6", "#f59e0b", "#ef4444", "#8b5cf6", "#06b6d4", "#ec4899"];

function formatCost(c: number): string {
  return `$${c.toFixed(4)}`;
}

function KpiCard({ title, value, subtitle, icon }: { title: string; value: string; subtitle: string; icon: React.ReactNode }) {
  return (
    <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-6">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-gray-500">{title}</p>
          <p className="text-2xl font-bold text-gray-900 mt-1">{value}</p>
          <p className="text-xs text-gray-400 mt-1">{subtitle}</p>
        </div>
        <div className="p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">{icon}</div>
      </div>
    </div>
  );
}

export default function CostsPage(): JSX.Element {
  const [summary, setSummary] = useState<CostSummary | null>(null);
  const [timeseries, setTimeseries] = useState<Array<{ bucket: string; cost: number }>>([]);
  const [byModel, setByModel] = useState<ModelCostBreakdown[]>([]);
  const [byProvider, setByProvider] = useState<{ provider: string; total_cost: number; span_count: number }[]>([]);
  const [byFeature, setByFeature] = useState<{ feature: string; total_cost: number; span_count: number }[]>([]);
  const [topRuns, setTopRuns] = useState<{ id: string; name: string; total_cost: number; span_count: number; status: string; total_tokens?: number }[]>([]);
  const [projection, setProjection] = useState<{ daily_burn: number; monthly_projection: number } | null>(null);
  const [budgets, setBudgets] = useState<Budget[]>([]);
  const [budgetStatuses, setBudgetStatuses] = useState<Record<string, BudgetStatus>>({});
  const [loading, setLoading] = useState(true);
  const [promptVersion, setPromptVersion] = useState("");
  const [dailyReport, setDailyReport] = useState<DailyCostReport | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const [s, ts, m, p, f, tr, pr, b, report] = await Promise.all([
          fetchCostSummary(),
          fetchCostTimeseries("day", 30),
          fetchCostByModel(),
          fetchCostByProvider(),
          fetchCostByFeature(),
          fetchTopExpensiveRuns(10),
          fetchCostProjection(),
          fetchBudgets(),
          fetchDailyCostReport(promptVersion || undefined),
        ]);
        setSummary(s);
        setTimeseries(ts.data);
        setByModel(m);
        setByProvider(p);
        setByFeature(f);
        setTopRuns(tr);
        setProjection(pr);
        setBudgets(b);
        setDailyReport(report);

        const statuses: Record<string, BudgetStatus> = {};
        for (const budget of b) {
          try {
            statuses[budget.id] = await fetchBudgetStatus(budget.id);
          } catch {
            // skip
          }
        }
        setBudgetStatuses(statuses);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    load();

    const interval = setInterval(load, 10000);
    return () => clearInterval(interval);
  }, [promptVersion]);

  if (loading) {
    return (
      <div className="p-6">
        <h2 className="text-2xl font-bold">Cost & FinOps</h2>
        <p className="text-gray-500 mt-2">Loading cost analytics...</p>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-8">
      <div>
        <h2 className="text-2xl font-bold text-gray-900">Cost & FinOps</h2>
        <p className="text-gray-500 mt-1">Track where your AI spend goes.</p>
      </div>

      <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-6">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <h3 className="text-lg font-semibold">Prompt Versions</h3>
            <p className="text-sm text-gray-500">Compare tagged LLM spend and filter the daily report.</p>
          </div>
          <label className="text-sm font-medium text-gray-700">
            Report filter
            <select
              className="ml-3 rounded-md border border-gray-300 bg-white px-3 py-2 text-sm"
              value={promptVersion}
              onChange={(event) => setPromptVersion(event.target.value)}
            >
              <option value="">All prompt versions</option>
              {Object.keys(summary?.by_prompt_version ?? {}).sort().map((version) => (
                <option key={version} value={version}>{version}</option>
              ))}
            </select>
          </label>
        </div>
        <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-3">
          {Object.entries(summary?.by_prompt_version ?? {}).sort(([a], [b]) => a.localeCompare(b)).map(([version, cost]) => (
            <div key={version} className="rounded-md bg-gray-50 p-4 dark:bg-gray-800">
              <p className="text-sm font-medium text-gray-700 dark:text-gray-200">{version}</p>
              <p className="mt-1 text-xl font-bold">{formatCost(cost)}</p>
            </div>
          ))}
        </div>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <KpiCard
          title="Total Cost"
          value={summary ? formatCost(summary.total_cost) : "$0.00"}
          subtitle="All time"
          icon={<DollarSign className="h-6 w-6 text-emerald-600" />}
        />
        <KpiCard
          title="Total Tokens"
          value={summary ? summary.total_tokens.toLocaleString() : "0"}
          subtitle="All time"
          icon={<Coins className="h-6 w-6 text-blue-600" />}
        />
        <KpiCard
          title="Total Spans"
          value={summary ? summary.total_spans.toLocaleString() : "0"}
          subtitle="Traced operations"
          icon={<BarChart3 className="h-6 w-6 text-amber-600" />}
        />
        <KpiCard
          title="Daily Burn"
          value={projection ? formatCost(projection.daily_burn) : "$0.00"}
          subtitle="Trailing 7d average"
          icon={<TrendingUp className="h-6 w-6 text-red-600" />}
        />
      </div>

      {/* Budgets */}
      {budgets.length > 0 && (
        <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-6">
          <h3 className="text-lg font-semibold mb-4">Budgets</h3>
          <div className="space-y-4">
            {budgets.map((b) => {
              const status = budgetStatuses[b.id];
              if (!status) return null;
              const pct = Math.min(status.percent_used, 100);
              const barColor = status.breached ? "bg-red-500" : status.alert_triggered ? "bg-amber-500" : "bg-emerald-500";
              return (
                <div key={b.id}>
                  <div className="flex justify-between text-sm mb-1">
                    <span className="font-medium">{b.name}</span>
                    <span className={status.breached ? "text-red-600" : status.alert_triggered ? "text-amber-600" : "text-emerald-600"}>
                      {status.percent_used.toFixed(1)}% of {formatCost(b.limit_usd)}
                    </span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2.5">
                    <div className={`h-2.5 rounded-full ${barColor}`} style={{ width: `${pct}%` }} />
                  </div>
                  {status.projected_monthly && (
                    <p className="text-xs text-gray-500 mt-1">
                      Projected monthly: {formatCost(status.projected_monthly)}
                    </p>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Charts row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Cost over time */}
        <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-6">
          <h3 className="text-lg font-semibold mb-4">Cost Over Time</h3>
          <ResponsiveContainer width="100%" height={250}>
            <LineChart data={timeseries}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="bucket" tick={{ fontSize: 12 }} />
              <YAxis tickFormatter={(v: number) => `$${v.toFixed(2)}`} tick={{ fontSize: 12 }} />
              <Tooltip formatter={(value: number) => formatCost(value)} />
              <Line type="monotone" dataKey="cost" stroke="#10b981" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Cost by model */}
        <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-6">
          <h3 className="text-lg font-semibold mb-4">Cost by Model</h3>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={byModel}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="model" tick={{ fontSize: 12 }} />
              <YAxis tickFormatter={(v: number) => `$${v.toFixed(2)}`} tick={{ fontSize: 12 }} />
              <Tooltip formatter={(value: number) => formatCost(value)} />
              <Bar dataKey="total_cost" fill="#3b82f6" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Cost by provider */}
        <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-6">
          <h3 className="text-lg font-semibold mb-4">Cost by Provider</h3>
          <ResponsiveContainer width="100%" height={250}>
            <PieChart>
              <Pie
                data={byProvider}
                dataKey="total_cost"
                nameKey="provider"
                cx="50%"
                cy="50%"
                outerRadius={80}
                label={({ provider, percent }: { provider: string; percent: number }) => `${provider} ${(percent * 100).toFixed(0)}%`}
              >
                {byProvider.map((_, i) => (
                  <Cell key={`cell-${i}`} fill={COLORS[i % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip formatter={(value: number) => formatCost(value)} />
            </PieChart>
          </ResponsiveContainer>
        </div>

        {/* Cost by feature */}
        <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-6">
          <h3 className="text-lg font-semibold mb-4">Cost by Feature</h3>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={byFeature}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="feature" tick={{ fontSize: 12 }} />
              <YAxis tickFormatter={(v: number) => `$${v.toFixed(2)}`} tick={{ fontSize: 12 }} />
              <Tooltip formatter={(value: number) => formatCost(value)} />
              <Bar dataKey="total_cost" fill="#8b5cf6" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Top expensive runs */}
      <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-6">
        <h3 className="text-lg font-semibold mb-4">Daily LLM Cost Report</h3>
        {Object.keys(dailyReport?.days ?? {}).length === 0 ? (
          <p className="text-gray-500 text-sm">No LLM traces match this prompt version.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200 bg-gray-50">
                  <th className="py-2 px-4 text-left text-xs font-semibold text-gray-500 uppercase">Day</th>
                  <th className="py-2 px-4 text-right text-xs font-semibold text-gray-500 uppercase">Requests</th>
                  <th className="py-2 px-4 text-right text-xs font-semibold text-gray-500 uppercase">Tokens</th>
                  <th className="py-2 px-4 text-right text-xs font-semibold text-gray-500 uppercase">Cost</th>
                  <th className="py-2 px-4 text-right text-xs font-semibold text-gray-500 uppercase">Avg latency</th>
                  <th className="py-2 px-4 text-right text-xs font-semibold text-gray-500 uppercase">p95</th>
                  <th className="py-2 px-4 text-right text-xs font-semibold text-gray-500 uppercase">Errors</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(dailyReport?.days ?? {}).sort(([a], [b]) => b.localeCompare(a)).map(([day, metrics]) => (
                  <tr key={day} className="border-b border-gray-100">
                    <td className="py-2 px-4 font-medium">{day}</td>
                    <td className="py-2 px-4 text-right">{metrics.total_requests.toLocaleString()}</td>
                    <td className="py-2 px-4 text-right">{metrics.total_tokens.toLocaleString()}</td>
                    <td className="py-2 px-4 text-right">{formatCost(metrics.estimated_cost)}</td>
                    <td className="py-2 px-4 text-right">{metrics.average_latency_ms.toFixed(1)} ms</td>
                    <td className="py-2 px-4 text-right">{metrics.p95_latency_ms.toFixed(1)} ms</td>
                    <td className="py-2 px-4 text-right">{(metrics.error_rate * 100).toFixed(1)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-6">
        <h3 className="text-lg font-semibold mb-4">Top Expensive Runs</h3>
        {topRuns.length === 0 ? (
          <p className="text-gray-500 text-sm">No runs yet.</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 bg-gray-50">
                <th className="py-2 px-4 text-left text-xs font-semibold text-gray-500 uppercase">Name</th>
                <th className="py-2 px-4 text-left text-xs font-semibold text-gray-500 uppercase">Status</th>
                <th className="py-2 px-4 text-left text-xs font-semibold text-gray-500 uppercase">Cost</th>
                <th className="py-2 px-4 text-left text-xs font-semibold text-gray-500 uppercase">Tokens</th>
                <th className="py-2 px-4 text-left text-xs font-semibold text-gray-500 uppercase">Spans</th>
              </tr>
            </thead>
            <tbody>
              {topRuns.map((run) => (
                <tr key={run.id} className="border-b border-gray-100">
                  <td className="py-2 px-4 font-medium">{run.name}</td>
                  <td className="py-2 px-4 capitalize">{run.status}</td>
                  <td className="py-2 px-4">{formatCost(run.total_cost)}</td>
                  <td className="py-2 px-4">{run.total_tokens?.toLocaleString() ?? "0"}</td>
                  <td className="py-2 px-4">{run.span_count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

"use client";

import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from "recharts";
import type { TraceResponse, SpanType } from "@/types";

interface CostBreakdownProps {
  spans: TraceResponse[];
}

interface CostGroup {
  type: SpanType;
  totalCost: number;
  count: number;
}

function getTypeLabel(type: SpanType): string {
  const labels: Record<SpanType, string> = {
    llm_call: "LLM Calls",
    tool_call: "Tool Calls",
    decision: "Decisions",
    retrieval: "Retrievals",
    custom: "Custom",
  };
  return labels[type];
}

function getTypeColor(type: SpanType): string {
  const colors: Record<SpanType, string> = {
    llm_call: "#a855f7",
    tool_call: "#3b82f6",
    decision: "#eab308",
    retrieval: "#22c55e",
    custom: "#6b7280",
  };
  return colors[type];
}

function groupCostsByType(spans: TraceResponse[]): CostGroup[] {
  const groups: Record<string, CostGroup> = {};

  for (const span of spans) {
    const cost: number = span.cost_usd ?? 0;
    if (!groups[span.span_type]) {
      groups[span.span_type] = { type: span.span_type, totalCost: 0, count: 0 };
    }
    groups[span.span_type].totalCost += cost;
    groups[span.span_type].count += 1;
  }

  return Object.values(groups);
}

export function CostBreakdown({ spans }: CostBreakdownProps): JSX.Element {
  const groups: CostGroup[] = groupCostsByType(spans);
  const totalCost: number = groups.reduce((sum, g) => sum + g.totalCost, 0);

  return (
    <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-6">
      <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Cost Breakdown</h3>

      {groups.length === 0 ? (
        <p className="text-gray-400 text-sm">No cost data available.</p>
      ) : (
        <div>
          <div className="h-48 mb-4">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={groups} margin={{ top: 5, right: 5, left: 5, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
                <XAxis
                  dataKey="type"
                  tickFormatter={getTypeLabel}
                  tick={{ fontSize: 11, fill: "#6b7280" }}
                />
                <YAxis
                  tick={{ fontSize: 11, fill: "#6b7280" }}
                  tickFormatter={(v) => `$${v.toFixed(3)}`}
                />
                <Tooltip
                  formatter={(value: number) => [`$${value.toFixed(4)}`, "Cost"]}
                  labelFormatter={getTypeLabel}
                />
                <Bar dataKey="totalCost" radius={[4, 4, 0, 0]}>
                  {groups.map((g) => (
                    <Cell key={g.type} fill={getTypeColor(g.type)} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="space-y-2">
            {groups.map((group) => {
              const pct = totalCost > 0 ? (group.totalCost / totalCost) * 100 : 0;
              return (
                <div key={group.type} className="flex justify-between text-sm">
                  <span className="text-gray-700">
                    {getTypeLabel(group.type)} ({group.count})
                  </span>
                  <span className="text-gray-500">
                    ${group.totalCost.toFixed(4)} ({pct.toFixed(1)}%)
                  </span>
                </div>
              );
            })}
            <div className="pt-2 border-t border-gray-100 flex justify-between text-sm font-semibold">
              <span>Total</span>
              <span>${totalCost.toFixed(4)}</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

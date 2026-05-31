"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import type { TraceResponse, SpanType, TokenUsage as TokenUsageType } from "@/types";

interface TokenUsageProps {
  spans: TraceResponse[];
}

interface TokenGroup {
  type: SpanType;
  promptTokens: number;
  completionTokens: number;
  totalTokens: number;
  count: number;
}

function groupTokensByType(spans: TraceResponse[]): TokenGroup[] {
  const groups: Record<string, TokenGroup> = {};

  for (const span of spans) {
    const usage: TokenUsageType | null = span.token_usage;
    if (!usage) continue;

    if (!groups[span.span_type]) {
      groups[span.span_type] = {
        type: span.span_type,
        promptTokens: 0,
        completionTokens: 0,
        totalTokens: 0,
        count: 0,
      };
    }

    groups[span.span_type].promptTokens += usage.prompt_tokens;
    groups[span.span_type].completionTokens += usage.completion_tokens;
    groups[span.span_type].totalTokens += usage.total_tokens;
    groups[span.span_type].count += 1;
  }

  return Object.values(groups);
}

function formatTokens(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return n.toString();
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

const chartData = [
  { key: "promptTokens", name: "Prompt", color: "#a78bfa" },
  { key: "completionTokens", name: "Completion", color: "#c4b5fd" },
] as const;

export function TokenUsage({ spans }: TokenUsageProps): JSX.Element {
  const groups: TokenGroup[] = groupTokensByType(spans);
  const grandTotal: number = groups.reduce((sum, g) => sum + g.totalTokens, 0);

  return (
    <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-6">
      <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Token Usage</h3>

      {groups.length === 0 ? (
        <p className="text-gray-400 text-sm">No token data available.</p>
      ) : (
        <div>
          <div className="h-48 mb-4">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={groups}
                margin={{ top: 5, right: 5, left: 5, bottom: 5 }}
                barCategoryGap="30%"
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
                <XAxis
                  dataKey="type"
                  tickFormatter={getTypeLabel}
                  tick={{ fontSize: 11, fill: "#6b7280" }}
                />
                <YAxis
                  tick={{ fontSize: 11, fill: "#6b7280" }}
                  tickFormatter={formatTokens}
                />
                <Tooltip formatter={(value: number) => [formatTokens(value)]} />
                <Legend
                  wrapperStyle={{ fontSize: "12px" }}
                  iconType="rect"
                />
                {chartData.map(({ key, name, color }) => (
                  <Bar
                    key={key}
                    dataKey={key}
                    name={name}
                    fill={color}
                    radius={[3, 3, 0, 0]}
                    stackId="tokens"
                  />
                ))}
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="space-y-2">
            {groups.map((group) => {
              const pct = grandTotal > 0 ? (group.totalTokens / grandTotal) * 100 : 0;
              return (
                <div key={group.type}>
                  <div className="flex justify-between text-sm mb-1">
                    <span className="text-gray-700">
                      {getTypeLabel(group.type)}
                    </span>
                    <span className="text-gray-500">
                      {formatTokens(group.totalTokens)} ({pct.toFixed(1)}%)
                    </span>
                  </div>
                  <div className="flex gap-4 text-xs text-gray-400">
                    <span>Prompt: {formatTokens(group.promptTokens)}</span>
                    <span>Completion: {formatTokens(group.completionTokens)}</span>
                  </div>
                </div>
              );
            })}
            <div className="pt-2 border-t border-gray-100 flex justify-between text-sm font-semibold">
              <span>Total Tokens</span>
              <span>{formatTokens(grandTotal)}</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

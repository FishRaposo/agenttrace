"use client";

import { useState } from "react";
import type { TraceResponse, SpanType, SpanStatus } from "@/types";

interface RunTimelineProps {
  spans: TraceResponse[];
}

function formatDuration(ms: number | null): string {
  if (ms === null) return "—";
  if (ms < 1000) return `${ms.toFixed(0)}ms`;
  return `${(ms / 1000).toFixed(2)}s`;
}

function formatCost(cost: number | null): string {
  if (cost === null || cost === 0) return "";
  return `$${cost.toFixed(4)}`;
}

function getSpanTypeColor(type: SpanType): string {
  const colors: Record<SpanType, string> = {
    llm_call: "bg-purple-500",
    tool_call: "bg-blue-500",
    decision: "bg-yellow-500",
    retrieval: "bg-green-500",
    custom: "bg-gray-500",
  };
  return colors[type];
}

function getStatusIcon(status: SpanStatus): string {
  const icons: Record<SpanStatus, string> = {
    completed: "✓",
    started: "●",
    error: "✕",
  };
  return icons[status];
}

interface SpanNode {
  span: TraceResponse;
  children: SpanNode[];
  depth: number;
}

function buildSpanTree(spans: TraceResponse[]): SpanNode[] {
  const byParent: Record<string, TraceResponse[]> = {};
  const roots: TraceResponse[] = [];

  for (const span of spans) {
    if (span.parent_span_id) {
      byParent[span.parent_span_id] = byParent[span.parent_span_id] || [];
      byParent[span.parent_span_id].push(span);
    } else {
      roots.push(span);
    }
  }

  function buildNode(span: TraceResponse, depth: number): SpanNode {
    return {
      span,
      children: (byParent[span.span_id] || []).map((child) => buildNode(child, depth + 1)),
      depth,
    };
  }

  return roots.map((root) => buildNode(root, 0));
}

function SpanRow({
  node,
  maxDuration,
  totalRunCost,
  expanded,
  onToggle,
}: {
  node: SpanNode;
  maxDuration: number;
  totalRunCost: number;
  expanded: Set<string>;
  onToggle: (id: string) => void;
}): JSX.Element {
  const { span, children, depth } = node;
  const barWidth = maxDuration > 0 ? ((span.duration_ms ?? 0) / maxDuration) * 100 : 0;
  const isError = span.status === "error";
  const hasChildren = children.length > 0;
  const isExpanded = expanded.has(span.id);
  const costPct = totalRunCost > 0 && span.cost_usd ? (span.cost_usd / totalRunCost) * 100 : 0;

  return (
    <div>
      <div
        className={`group flex items-center gap-2 py-1 px-2 rounded hover:bg-gray-50 dark:hover:bg-gray-800 ${
          isError ? "bg-red-50 dark:bg-red-900/20 border border-red-100 dark:border-red-900" : ""
        }`}
        style={{ paddingLeft: `${depth * 20 + 8}px` }}
        title={span.error || undefined}
      >
        {/* Expand toggle */}
        <button
          onClick={() => hasChildren && onToggle(span.id)}
          className={`w-4 h-4 text-xs text-gray-400 shrink-0 ${hasChildren ? "cursor-pointer" : "invisible"}`}
        >
          {isExpanded ? "▼" : "▶"}
        </button>

        {/* Duration label */}
        <div className="w-16 text-xs text-gray-500 shrink-0 text-right">
          {formatDuration(span.duration_ms)}
        </div>

        {/* Bar */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <div className="w-full bg-gray-100 dark:bg-gray-800 rounded-full h-7 relative overflow-hidden">
              <div
                className={`h-7 rounded-full ${getSpanTypeColor(span.span_type)} ${
                  isError ? "ring-2 ring-red-500 ring-offset-1" : ""
                } opacity-90 flex items-center px-3`}
                style={{ width: `${Math.max(barWidth, 3)}%` }}
              >
                <span className="text-xs text-white font-medium truncate">
                  {span.name}
                </span>
                {span.cost_usd ? (
                  <span className="ml-auto text-[10px] text-white/90 font-mono shrink-0">
                    {formatCost(span.cost_usd)}
                  </span>
                ) : null}
              </div>
            </div>
            <span className="text-sm">{getStatusIcon(span.status)}</span>
          </div>
        </div>

        {/* Cost contribution */}
        <div className="w-20 text-right shrink-0">
          {costPct > 0 ? (
            <span className="text-[10px] text-gray-400 font-mono">
              {costPct.toFixed(1)}%
            </span>
          ) : null}
        </div>

        {/* Type badge */}
        <span className="text-[10px] font-mono text-gray-400 shrink-0 uppercase">
          {span.span_type}
        </span>
      </div>

      {/* Children */}
      {hasChildren && isExpanded && (
        <div>
          {children.map((child) => (
            <SpanRow
              key={child.span.id}
              node={child}
              maxDuration={maxDuration}
              totalRunCost={totalRunCost}
              expanded={expanded}
              onToggle={onToggle}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export function RunTimeline({ spans }: RunTimelineProps): JSX.Element {
  const [expanded, setExpanded] = useState<Set<string>>(new Set());

  if (spans.length === 0) {
    return (
      <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-6">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Timeline</h3>
        <p className="text-gray-400 dark:text-gray-500 text-sm">No spans recorded.</p>
      </div>
    );
  }

  const maxDuration = Math.max(...spans.map((s) => s.duration_ms ?? 0));
  const totalRunCost = spans.reduce((sum, s) => sum + (s.cost_usd ?? 0), 0);
  const tree = buildSpanTree(spans);

  function toggle(id: string) {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }

  return (
    <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Timeline</h3>
        <div className="flex gap-3 text-xs text-gray-500">
          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-purple-500" /> LLM</span>
          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-blue-500" /> Tool</span>
          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-yellow-500" /> Decision</span>
          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-green-500" /> Retrieval</span>
          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-gray-500" /> Custom</span>
        </div>
      </div>
      <div className="space-y-0.5">
        {tree.map((node) => (
          <SpanRow
            key={node.span.id}
            node={node}
            maxDuration={maxDuration}
            totalRunCost={totalRunCost}
            expanded={expanded}
            onToggle={toggle}
          />
        ))}
      </div>
    </div>
  );
}

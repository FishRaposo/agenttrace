"use client";

import type { TraceResponse, SpanType, SpanStatus } from "@/types";

interface RunTimelineProps {
  spans: TraceResponse[];
}

function formatDuration(ms: number | null): string {
  if (ms === null) return "—";
  if (ms < 1000) return `${ms.toFixed(0)}ms`;
  return `${(ms / 1000).toFixed(2)}s`;
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

export function RunTimeline({ spans }: RunTimelineProps): JSX.Element {
  if (spans.length === 0) {
    return (
      <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-6">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
          Timeline
        </h3>
        <p className="text-gray-400 dark:text-gray-500 text-sm">No spans recorded.</p>
      </div>
    );
  }

  const maxDuration: number = Math.max(
    ...spans.map((s) => s.duration_ms ?? 0)
  );

  return (
    <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-6">
      <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Timeline</h3>
      <div className="space-y-3">
        {spans.map((span) => {
          const barWidth: number =
            maxDuration > 0
              ? ((span.duration_ms ?? 0) / maxDuration) * 100
              : 0;

          return (
            <div key={span.id} className="flex items-center gap-3">
              <div className="w-24 text-xs text-gray-500 shrink-0">
                {formatDuration(span.duration_ms)}
              </div>
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <div className="w-full bg-gray-100 rounded-full h-6 relative">
                    <div
                      className={`h-6 rounded-full ${getSpanTypeColor(
                        span.span_type
                      )} opacity-80 flex items-center px-3`}
                      style={{ width: `${Math.max(barWidth, 5)}%` }}
                    >
                      <span className="text-xs text-white font-medium truncate">
                        {span.name}
                      </span>
                    </div>
                  </div>
                  <span className="text-sm">
                    {getStatusIcon(span.status)}
                  </span>
                </div>
              </div>
              <span className="text-xs font-mono text-gray-400 shrink-0">
                {span.span_type}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

"use client";

import { useState } from "react";
import type { TraceResponse, SpanType } from "@/types";

interface SpanDetailProps {
  spans: TraceResponse[];
}

function getSpanTypeClass(type: SpanType): string {
  const classes: Record<SpanType, string> = {
    llm_call: "span-llm_call",
    tool_call: "span-tool_call",
    decision: "span-decision",
    retrieval: "span-retrieval",
    custom: "span-custom",
  };
  return classes[type];
}

function formatJson(data: unknown): string {
  if (data === null || data === undefined) return "—";
  try {
    return JSON.stringify(data, null, 2);
  } catch {
    return String(data);
  }
}

export function SpanDetail({ spans }: SpanDetailProps): JSX.Element {
  const [selectedId, setSelectedId] = useState<string | null>(
    spans.length > 0 ? spans[0].id : null
  );

  const selected: TraceResponse | undefined = spans.find(
    (s) => s.id === selectedId
  );

  if (spans.length === 0) {
    return (
      <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-6">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
          Span Details
        </h3>
        <p className="text-gray-400 dark:text-gray-500 text-sm">No spans to display.</p>
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-6">
      <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
        Span Details
      </h3>

      <div className="flex gap-2 mb-4 flex-wrap">
        {spans.map((span) => (
          <button
            key={span.id}
            onClick={() => setSelectedId(span.id)}
            className={`span-type-badge ${getSpanTypeClass(
              span.span_type
            )} cursor-pointer ${
              selectedId === span.id ? "ring-2 ring-trace-500" : ""
            }`}
          >
            {span.name}
          </button>
        ))}
      </div>

      {selected && (
        <div className="space-y-4">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div>
              <span className="text-gray-500">Status</span>
              <p className="font-medium">{selected.status}</p>
            </div>
            <div>
              <span className="text-gray-500">Duration</span>
              <p className="font-medium">
                {selected.duration_ms !== null
                  ? `${selected.duration_ms.toFixed(1)}ms`
                  : "—"}
              </p>
            </div>
            <div>
              <span className="text-gray-500">Cost</span>
              <p className="font-medium">
                {selected.cost_usd !== null
                  ? `$${selected.cost_usd.toFixed(4)}`
                  : "—"}
              </p>
            </div>
            <div>
              <span className="text-gray-500">Tokens</span>
              <p className="font-medium">
                {selected.token_usage?.total_tokens.toLocaleString() ?? "—"}
              </p>
            </div>
          </div>

          {selected.error && (
            <div className="bg-red-50 border border-red-200 rounded-md p-3 text-sm text-red-700">
              {selected.error}
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <h4 className="text-sm font-semibold text-gray-700 mb-2">
                Input
              </h4>
              <pre className="bg-gray-50 rounded-md p-3 text-xs overflow-auto max-h-64">
                {formatJson(selected.input_data)}
              </pre>
            </div>
            <div>
              <h4 className="text-sm font-semibold text-gray-700 mb-2">
                Output
              </h4>
              <pre className="bg-gray-50 rounded-md p-3 text-xs overflow-auto max-h-64">
                {formatJson(selected.output_data)}
              </pre>
            </div>
          </div>

          {selected.metadata && (
            <div>
              <h4 className="text-sm font-semibold text-gray-700 mb-2">
                Metadata
              </h4>
              <pre className="bg-gray-50 rounded-md p-3 text-xs overflow-auto max-h-48">
                {formatJson(selected.metadata)}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

"use client";

import { useEffect, useRef, useState } from "react";
import { Pause, Play, Radio } from "lucide-react";
import { streamTraces } from "@/lib/api";
import type { TraceResponse } from "@/types";

function formatCost(c: number | null): string {
  if (c === null) return "$0.0000";
  return `$${c.toFixed(4)}`;
}

function formatDuration(ms: number | null): string {
  if (ms === null) return "—";
  if (ms < 1000) return `${Math.round(ms)}ms`;
  return `${(ms / 1000).toFixed(2)}s`;
}

const SPAN_TYPE_COLOR: Record<string, string> = {
  llm_call: "bg-blue-100 text-blue-800",
  tool_call: "bg-emerald-100 text-emerald-800",
  decision: "bg-amber-100 text-amber-800",
  retrieval: "bg-purple-100 text-purple-800",
  custom: "bg-gray-100 text-gray-800",
};

export default function LivePage(): JSX.Element {
  const [traces, setTraces] = useState<TraceResponse[]>([]);
  const [paused, setPaused] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (paused) return;

    const cleanup = streamTraces((trace) => {
      setTraces((prev) => {
        const next = [trace, ...prev];
        return next.slice(0, 100);
      });
    });

    return cleanup;
  }, [paused]);

  useEffect(() => {
    if (!paused && scrollRef.current) {
      scrollRef.current.scrollTop = 0;
    }
  }, [traces, paused]);

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <Radio className="h-6 w-6 text-red-500" />
            Live Tail
          </h2>
          <p className="text-gray-500 mt-1">Real-time incoming trace spans.</p>
        </div>
        <button
          onClick={() => setPaused(!paused)}
          className="flex items-center gap-2 px-4 py-2 rounded-lg border border-gray-200 hover:bg-gray-50 text-sm font-medium"
        >
          {paused ? <Play className="h-4 w-4" /> : <Pause className="h-4 w-4" />}
          {paused ? "Resume" : "Pause"}
        </button>
      </div>

      {paused && (
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 text-sm text-amber-700">
          Live tail is paused. Click Resume to continue receiving spans.
        </div>
      )}

      <div
        ref={scrollRef}
        className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 overflow-auto"
        style={{ maxHeight: "70vh" }}
      >
        <table className="w-full text-sm">
          <thead className="sticky top-0 bg-white dark:bg-gray-900 z-10">
            <tr className="border-b border-gray-200">
              <th className="py-3 px-4 text-left text-xs font-semibold text-gray-500 uppercase">Type</th>
              <th className="py-3 px-4 text-left text-xs font-semibold text-gray-500 uppercase">Name</th>
              <th className="py-3 px-4 text-left text-xs font-semibold text-gray-500 uppercase">Run</th>
              <th className="py-3 px-4 text-left text-xs font-semibold text-gray-500 uppercase">Duration</th>
              <th className="py-3 px-4 text-left text-xs font-semibold text-gray-500 uppercase">Cost</th>
              <th className="py-3 px-4 text-left text-xs font-semibold text-gray-500 uppercase">Status</th>
            </tr>
          </thead>
          <tbody>
            {traces.length === 0 ? (
              <tr>
                <td colSpan={6} className="py-8 text-center text-gray-400 text-sm">
                  Waiting for spans...
                </td>
              </tr>
            ) : (
              traces.map((t) => (
                <tr key={t.id} className="border-b border-gray-100 hover:bg-gray-50">
                  <td className="py-2 px-4">
                    <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${SPAN_TYPE_COLOR[t.span_type] || SPAN_TYPE_COLOR.custom}`}>
                      {t.span_type}
                    </span>
                  </td>
                  <td className="py-2 px-4 font-medium truncate max-w-xs" title={String(t.name)}>
                    {t.name}
                  </td>
                  <td className="py-2 px-4 text-gray-500 font-mono text-xs truncate max-w-[120px]">
                    {t.run_id.slice(0, 8)}
                  </td>
                  <td className="py-2 px-4 text-gray-600">{formatDuration(t.duration_ms)}</td>
                  <td className="py-2 px-4 text-gray-600">{formatCost(t.cost_usd)}</td>
                  <td className="py-2 px-4 capitalize">{t.status}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

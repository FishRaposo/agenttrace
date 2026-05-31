"use client";

import { useEffect, useState } from "react";
import { getReplayData } from "@/lib/api";
import type { ReplayData, SpanType, SpanStatus } from "@/types";
import { Play, SkipBack, SkipForward, ChevronRight, ChevronDown } from "lucide-react";

interface PromptReplayProps {
  runId: string;
}

function formatJson(data: unknown): string {
  if (data === null || data === undefined) return "—";
  try {
    return JSON.stringify(data, null, 2);
  } catch {
    return String(data);
  }
}

function getSpanTypeLabel(type: SpanType): string {
  const labels: Record<SpanType, string> = {
    llm_call: "LLM Call",
    tool_call: "Tool Call",
    decision: "Decision",
    retrieval: "Retrieval",
    custom: "Custom",
  };
  return labels[type];
}

function getStatusColor(status: SpanStatus): string {
  const colors: Record<SpanStatus, string> = {
    completed: "text-green-600",
    error: "text-red-600",
    started: "text-blue-600",
  };
  return colors[status];
}

export function PromptReplay({ runId }: PromptReplayProps): JSX.Element {
  const [replayData, setReplayData] = useState<ReplayData | null>(null);
  const [currentStep, setCurrentStep] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedSteps, setExpandedSteps] = useState<Set<number>>(new Set());

  useEffect(() => {
    async function loadData() {
      setLoading(true);
      setError(null);
      try {
        const data = await getReplayData(runId);
        setReplayData(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load replay data");
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, [runId]);

  const toggleExpand = (index: number) => {
    const newExpanded = new Set(expandedSteps);
    if (newExpanded.has(index)) {
      newExpanded.delete(index);
    } else {
      newExpanded.add(index);
    }
    setExpandedSteps(newExpanded);
  };

  const nextStep = () => {
    if (replayData && currentStep < replayData.steps.length - 1) {
      setCurrentStep(currentStep + 1);
      setExpandedSteps(new Set([currentStep + 1]));
    }
  };

  const prevStep = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1);
      setExpandedSteps(new Set([currentStep - 1]));
    }
  };

  if (loading) {
    return (
      <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-6">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
          Prompt Replay
        </h3>
        <p className="text-gray-400 text-sm">Loading replay data...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-6">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
          Prompt Replay
        </h3>
        <p className="text-red-500 text-sm">{error}</p>
      </div>
    );
  }

  if (!replayData) {
    return <div className="text-gray-400 text-sm">No replay data available.</div>;
  }

  const currentStepData = replayData.steps[currentStep];
  const progress = ((currentStep + 1) / replayData.total_steps) * 100;

  return (
    <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
          Prompt Replay
        </h3>
        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-500">
            Step {currentStep + 1} of {replayData.total_steps}
          </span>
        </div>
      </div>

      <div className="mb-4">
        <div className="h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
          <div
            className="h-full bg-trace-600 transition-all duration-300"
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>

      <div className="flex items-center justify-center gap-4 mb-6">
        <button
          onClick={prevStep}
          disabled={currentStep === 0}
          className="p-2 rounded-lg bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          <SkipBack className="h-5 w-5" />
        </button>
        <button
          onClick={nextStep}
          className="p-3 rounded-lg bg-trace-600 text-white hover:bg-trace-700 transition-colors"
        >
          <Play className="h-5 w-5" />
        </button>
        <button
          onClick={nextStep}
          disabled={currentStep === replayData.steps.length - 1}
          className="p-2 rounded-lg bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          <SkipForward className="h-5 w-5" />
        </button>
      </div>

      {currentStepData && (
        <div className="space-y-4">
          <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
            <div className="flex items-center justify-between mb-2">
              <h4 className="font-medium text-gray-900 dark:text-white">
                {currentStepData.name}
              </h4>
              <span className="text-xs px-2 py-1 rounded bg-purple-100 dark:bg-purple-900 text-purple-800 dark:text-purple-200">
                {getSpanTypeLabel(currentStepData.span_type)}
              </span>
            </div>
            <div className="flex items-center gap-4 text-sm text-gray-500">
              <span>Status: <span className={getStatusColor(currentStepData.status)}>{currentStepData.status}</span></span>
              {currentStepData.error && (
                <span className="text-red-500">Error: {currentStepData.error}</span>
              )}
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
                Input
              </h4>
              <pre className="bg-gray-50 dark:bg-gray-800 rounded-md p-3 text-xs overflow-auto max-h-64">
                {formatJson(currentStepData.input_data)}
              </pre>
            </div>
            <div>
              <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
                Output
              </h4>
              <pre className="bg-gray-50 dark:bg-gray-800 rounded-md p-3 text-xs overflow-auto max-h-64">
                {formatJson(currentStepData.output_data)}
              </pre>
            </div>
          </div>

          {currentStepData.metadata && (
            <div>
              <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
                Metadata
              </h4>
              <pre className="bg-gray-50 dark:bg-gray-800 rounded-md p-3 text-xs overflow-auto max-h-48">
                {formatJson(currentStepData.metadata)}
              </pre>
            </div>
          )}
        </div>
      )}

      <div className="mt-6 border-t border-gray-200 dark:border-gray-700 pt-4">
        <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">
          All Steps
        </h4>
        <div className="space-y-2 max-h-64 overflow-y-auto">
          {replayData.steps.map((step, index) => (
            <div
              key={step.id}
              className={`border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden ${
                index === currentStep ? "ring-2 ring-trace-500" : ""
              }`}
            >
              <button
                onClick={() => {
                  setCurrentStep(index);
                  toggleExpand(index);
                }}
                className="w-full px-4 py-3 flex items-center justify-between hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <span className="text-sm font-mono text-gray-500">
                    {index + 1}.
                  </span>
                  <span className="text-sm font-medium text-gray-900 dark:text-white">
                    {step.name}
                  </span>
                  <span className="text-xs px-2 py-0.5 rounded bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400">
                    {getSpanTypeLabel(step.span_type)}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`text-xs ${getStatusColor(step.status)}`}>
                    {step.status}
                  </span>
                  {expandedSteps.has(index) ? (
                    <ChevronDown className="h-4 w-4 text-gray-400" />
                  ) : (
                    <ChevronRight className="h-4 w-4 text-gray-400" />
                  )}
                </div>
              </button>
              {expandedSteps.has(index) && (
                <div className="px-4 py-3 bg-gray-50 dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700">
                  <div className="grid grid-cols-2 gap-4 text-xs">
                    <div>
                      <span className="text-gray-500">Input:</span>
                      <pre className="mt-1 overflow-auto max-h-32">{formatJson(step.input_data)}</pre>
                    </div>
                    <div>
                      <span className="text-gray-500">Output:</span>
                      <pre className="mt-1 overflow-auto max-h-32">{formatJson(step.output_data)}</pre>
                    </div>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

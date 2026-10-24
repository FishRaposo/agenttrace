"use client";
import { useEffect, useState } from "react";
import { readApi } from "./api";
import { usePortfolio } from "./portfolio-state";
export function useData<T>(path: string | null, cohortScoped = false) {
  const state = usePortfolio();
  const [result, setResult] = useState<{
    data: T | null;
    error: string | null;
    loading: boolean;
  }>({ data: null, error: null, loading: true });
  const [retry, setRetry] = useState(0);
  const query =
    path && cohortScoped && state.source === "connected" && state.cohort
      ? `${path}${path.includes("?") ? "&" : "?"}cohort_id=${encodeURIComponent(state.cohort)}`
      : path;
  useEffect(() => {
    if (!state.ready || !query) return;
    const controller = new AbortController();
    setResult({ data: null, error: null, loading: true });
    readApi<T>(query, { signal: controller.signal })
      .then((data) => {
        if (!controller.signal.aborted)
          setResult({ data, error: null, loading: false });
      })
      .catch((error) => {
        if (!controller.signal.aborted)
          setResult({
            data: null,
            error:
              error instanceof Error
                ? error.message
                : "Unable to read collector data.",
            loading: false,
          });
      });
    return () => controller.abort();
  }, [query, state.ready, state.source, state.scenario, state.version, retry]);
  return { ...result, retry: () => setRetry((value) => value + 1) };
}

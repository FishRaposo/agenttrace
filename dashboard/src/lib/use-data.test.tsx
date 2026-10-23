import { describe, expect, it, vi, afterEach } from "vitest";
import { render, screen, waitFor, act } from "@testing-library/react";
import { useData } from "./use-data";
import { setPortfolio } from "./portfolio-state";
import { isDemoMode, streamTraces } from "./api";
afterEach(() => vi.unstubAllGlobals());
function Probe() {
  const result = useData<{ total: number }>("/api/runs?limit=100", true);
  return <span>{result.data?.total ?? "loading"}</span>;
}
describe("obsolete transport work", () => {
  it("aborts the old request and cannot render its late successful result after entering sample mode", async () => {
    setPortfolio({ source: "connected", ready: true, cohort: "old-cohort" });
    let resolve!: (value: unknown) => void;
    let signal: AbortSignal | undefined;
    vi.stubGlobal(
      "fetch",
      vi.fn((_url, options) => {
        signal = options.signal;
        return new Promise((done) => {
          resolve = done;
        });
      }),
    );
    render(<Probe />);
    await waitFor(() => expect(signal).toBeDefined());
    act(() => setPortfolio({ source: "sample" }));
    await screen.findByText("20");
    expect(signal?.aborted).toBe(true);
    await act(async () =>
      resolve({ ok: true, status: 200, json: async () => ({ total: 999 }) }),
    );
    expect(screen.getByText("20")).toBeInTheDocument();
    expect(screen.queryByText("999")).toBeNull();
  });
  it("does not change source or synthesize events after a collector stream failure", () => {
    setPortfolio({ source: "connected" });
    let instance!: {
      onerror: null | (() => void);
      close: ReturnType<typeof vi.fn>;
    };
    vi.stubGlobal(
      "EventSource",
      class {
        onerror = null;
        onopen = null;
        onmessage = null;
        close = vi.fn();
        constructor() {
          instance = this;
        }
      },
    );
    const event = vi.fn();
    const error = vi.fn();
    const close = streamTraces(event, {
      cursor: "41",
      cohort: "real",
      onError: error,
    });
    instance.onerror?.();
    expect(isDemoMode()).toBe(false);
    expect(event).not.toHaveBeenCalled();
    expect(error).toHaveBeenCalledWith(expect.stringContaining("Reconnecting"));
    close();
    expect(instance.close).toHaveBeenCalledOnce();
  });
});

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { fetchStats, fetchRuns, isDemoMode, subscribeDemoMode } from "@/lib/api";

describe("api client demo-mode fallback", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns parsed JSON when the backend responds", async () => {
    const payload = {
      total_runs: 7,
      total_cost: 1.23,
      total_tokens: 999,
      avg_duration_ms: 100,
    };
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => payload,
      })
    );
    const stats = await fetchStats();
    expect(stats.total_runs).toBe(7);
  });

  it("falls back to demo data and activates demo mode on network failure", async () => {
    let observed = false;
    const unsub = subscribeDemoMode((active) => {
      if (active) observed = true;
    });
    vi.stubGlobal(
      "fetch",
      vi.fn().mockRejectedValue(new TypeError("Failed to fetch"))
    );

    const runs = await fetchRuns(5, 0);
    expect(runs.runs.length).toBeGreaterThan(0);
    expect(isDemoMode()).toBe(true);
    expect(observed).toBe(true);
    unsub();
  });

  it("short-circuits to demo fixtures once demo mode is active", async () => {
    // Demo mode is now active from the previous test; fetch must not be called.
    const spy = vi.fn();
    vi.stubGlobal("fetch", spy);
    const stats = await fetchStats();
    expect(stats).toBeDefined();
    expect(spy).not.toHaveBeenCalled();
  });
});

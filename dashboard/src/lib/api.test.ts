import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { fetchStats, fetchRuns, isDemoMode, selectDataSource } from "@/lib/api";
afterEach(() => {
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
});
beforeEach(() => {
  selectDataSource("connected");
  vi.restoreAllMocks();
});
describe("explicit data sources", () => {
  it("keeps a forced offline build local even if a caller requests connected mode", async () => {
    vi.stubEnv("NEXT_PUBLIC_DEMO_MODE", "1");
    selectDataSource("connected");
    const fetch = vi.fn();
    vi.stubGlobal("fetch", fetch);
    expect((await fetchRuns(100)).total).toBe(20);
    expect(fetch).not.toHaveBeenCalled();
  });
  it("returns the real response without inventing provenance", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({ total_runs: 7 }),
      }),
    );
    expect((await fetchStats()).total_runs).toBe(7);
    expect(isDemoMode()).toBe(false);
  });
  it("keeps a failed collector an error", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("offline")));
    await expect(fetchRuns()).rejects.toThrow("offline");
    expect(isDemoMode()).toBe(false);
  });
  it("makes zero backend calls only after explicit sample selection", async () => {
    selectDataSource("sample");
    const fetch = vi.fn();
    vi.stubGlobal("fetch", fetch);
    expect((await fetchRuns(100)).total).toBe(20);
    expect(fetch).not.toHaveBeenCalled();
  });
});

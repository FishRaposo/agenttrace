import { afterEach, describe, expect, it, vi } from "vitest";

afterEach(() => {
  vi.unstubAllGlobals();
  vi.resetModules();
});

describe("connected truth boundary", () => {
  it("keeps a failed collector request an error instead of presenting successful fixtures", async () => {
    vi.stubEnv("NEXT_PUBLIC_DEMO_MODE", "0");
    const api = await import("./api");
    vi.stubGlobal(
      "fetch",
      vi.fn().mockRejectedValue(new TypeError("Collector unavailable")),
    );
    await expect(api.fetchRuns()).rejects.toThrow("Collector unavailable");
    expect(api.isDemoMode()).toBe(false);
  });
});

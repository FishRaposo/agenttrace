"use client";
import { useSyncExternalStore } from "react";
import type { Scenario } from "./demo-scenarios";

export const SOURCE_KEY = "agenttrace.preferences.v1";
export interface PortfolioState {
  source: "sample" | "connected";
  scenario: Scenario;
  cohort: string;
  cohorts: string[];
  tour: number;
  version: number;
  ready: boolean;
}
const initial: PortfolioState = {
  source: process.env.NEXT_PUBLIC_DEMO_MODE === "1" ? "sample" : "connected",
  scenario: "incident",
  cohort: "",
  cohorts: [],
  tour: -1,
  version: 0,
  ready: false,
};
let state = initial;
const listeners = new Set<() => void>();
export function getPortfolioState() {
  return state;
}
export function subscribePortfolio(listener: () => void) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}
export function setPortfolio(update: Partial<PortfolioState>) {
  state = { ...state, ...update, version: state.version + 1 };
  if (process.env.NEXT_PUBLIC_DEMO_MODE === "1")
    state = { ...state, source: "sample" };
  if (typeof window !== "undefined") {
    try {
      localStorage.setItem(
        SOURCE_KEY,
        JSON.stringify({
          source: state.source,
          cohort: state.cohort,
          cohorts: state.cohorts,
        }),
      );
    } catch {
      /* browser storage may be disabled */
    }
  }
  listeners.forEach((listener) => listener());
}
export function hydratePortfolio() {
  if (state.ready) return;
  let saved: Partial<PortfolioState> = {};
  try {
    saved = JSON.parse(localStorage.getItem(SOURCE_KEY) ?? "{}");
  } catch {
    /* invalid preference is ignored */
  }
  setPortfolio({
    source:
      process.env.NEXT_PUBLIC_DEMO_MODE === "1"
        ? "sample"
        : saved.source === "sample"
          ? "sample"
          : "connected",
    cohort: typeof saved.cohort === "string" ? saved.cohort : "",
    cohorts: Array.isArray(saved.cohorts)
      ? saved.cohorts.filter((v) => typeof v === "string")
      : [],
    ready: true,
  });
}
export function resetSample() {
  setPortfolio({ scenario: "incident", tour: -1 });
}
export function usePortfolio() {
  return useSyncExternalStore(
    subscribePortfolio,
    getPortfolioState,
    () => initial,
  );
}

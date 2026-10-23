"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  Activity,
  ArrowRight,
  RotateCcw,
  Radio,
  ChevronRight,
} from "lucide-react";
import {
  hydratePortfolio,
  resetSample,
  setPortfolio,
  usePortfolio,
} from "@/lib/portfolio-state";
import { scenarios } from "@/lib/demo-scenarios";
const nav = [
  { href: "/", label: "Overview" },
  { href: "/runs", label: "Runs" },
  { href: "/costs", label: "Costs" },
  { href: "/live", label: "Live" },
  { href: "/workflow", label: "Actual workflow" },
];
const tour = [
  {
    title: "Twenty requests, separate stories",
    body: "These lanes overlap in time. Each request keeps its own run, spans and correlation. Select request18 to find the retrieval failure.",
    href: "/runs",
  },
  {
    title: "Find the failing stage",
    body: "Request18 stops at retrieval. Its safe error explains why generation never started. Select a stage to inspect its correlation and capture summary.",
    href: "/runs/sample-incident-request-18",
  },
  {
    title: "Compare the repair",
    body: "Open Compare repair. Retrieval now completes and generation can proceed. Timeout and cancellation remain separate failures; the repair does not fix them.",
    href: "/runs/sample-incident-request-18",
  },
  {
    title: "Inspect the remaining outcomes",
    body: "Request19 times out; request20 is cancelled. These are terminal outcomes, never completed successes. Costs use the same selected cohort.",
    href: "/runs",
  },
  {
    title: "Reproduce the engineering",
    body: "The preview is fixed sample data. Run the packaged workload to exercise real asyncio concurrency, bounded delivery, collector persistence and this dashboard.",
    href: "/workflow",
  },
];
export function PortfolioShell({ children }: { children: React.ReactNode }) {
  const state = usePortfolio();
  const pathname = usePathname();
  const router = useRouter();
  const [dark, setDark] = useState(false);
  useEffect(() => {
    hydratePortfolio();
  }, []);
  useEffect(() => {
    document.documentElement.classList.toggle("dark", dark);
  }, [dark]);
  return (
    <div className="portfolio-shell">
      <a className="skip-link" href="#main-content">
        Skip to content
      </a>
      <header className="app-header">
        <Link className="brand" href="/">
          <span className="brand-mark">
            <Activity size={21} />
          </span>
          <span>
            AgentTrace<small>AI WORKFLOW OBSERVABILITY</small>
          </span>
        </Link>
        <div className="release-tag">0.2.0 · local release candidate</div>
        <button
          className="icon-button"
          aria-label="Toggle theme"
          onClick={() => setDark(!dark)}
        >
          {dark ? "Light" : "Dark"}
        </button>
      </header>
      <div className="workspace-bar">
        <nav aria-label="Main navigation">
          {nav.map((item) => (
            <Link
              key={item.href}
              className={
                pathname === item.href ||
                (item.href === "/runs" && pathname.startsWith("/runs/"))
                  ? "active"
                  : ""
              }
              href={item.href}
            >
              {item.label}
            </Link>
          ))}
        </nav>
        <label className="inline-label">
          Data source
          <select
            aria-label="Data source"
            data-testid="source-select"
            value={state.source}
            onChange={(event) => {
              setPortfolio({
                source: event.target.value as "sample" | "connected",
                tour: -1,
              });
              router.push("/");
            }}
          >
            <option
              value="connected"
              disabled={process.env.NEXT_PUBLIC_DEMO_MODE === "1"}
            >
              Connected collector
            </option>
            <option value="sample">Interactive sample data</option>
          </select>
        </label>
      </div>
      <div
        className={`source-bar ${state.source}`}
        role="status"
        data-testid="demo-mode-banner"
      >
        <span className="source-dot" />
        <strong>
          {state.source === "sample"
            ? "Interactive sample data"
            : "Connected local collector"}
        </strong>
        <span>
          {state.source === "sample"
            ? "Fixed telemetry · synthetic provider, tokens and prices · no backend calls"
            : "Real concurrency, export and persistence · bundled provider responses and prices are synthetic"}
        </span>
        {state.source === "sample" ? (
          <button
            onClick={() => {
              resetSample();
              router.push("/");
            }}
          >
            <RotateCcw size={14} />
            Reset demo
          </button>
        ) : null}
      </div>
      <div className="context-bar">
        {state.source === "sample" ? (
          <label>
            Scenario
            <select
              aria-label="Scenario"
              data-testid="scenario-select"
              value={state.scenario}
              onChange={(event) =>
                setPortfolio({
                  scenario: event.target.value as "incident" | "repaired",
                })
              }
            >
              {scenarios.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
            </select>
          </label>
        ) : (
          <label>
            Cohort
            <select
              aria-label="Cohort"
              data-testid="cohort-select"
              value={state.cohort}
              onChange={(event) => setPortfolio({ cohort: event.target.value })}
            >
              <option value="">All recorded history</option>
              {[
                ...new Set([...state.cohorts, state.cohort].filter(Boolean)),
              ].map((cohort) => (
                <option key={cohort} value={cohort}>
                  {cohort}
                </option>
              ))}
            </select>
          </label>
        )}
        <span>
          {state.source === "sample"
            ? scenarios.find((s) => s.id === state.scenario)?.description
            : state.cohort
              ? `Selected cohort ${state.cohort}`
              : "Legacy and current records remain accessible"}
        </span>
      </div>
      {state.source === "sample" && state.tour >= 0 ? (
        <section className="tour-card" aria-label="Guided investigation">
          <div>
            <small>
              GUIDED INVESTIGATION · {state.tour + 1}/{tour.length}
            </small>
            <h2>{tour[state.tour].title}</h2>
            <p>{tour[state.tour].body}</p>
          </div>
          <div className="button-row">
            <Link className="button" href={tour[state.tour].href}>
              Open step
              <ChevronRight size={15} />
            </Link>
            <button
              onClick={() => {
                const next = state.tour + 1;
                setPortfolio({ tour: next < tour.length ? next : -1 });
                if (next < tour.length) router.push(tour[next].href);
              }}
            >
              {state.tour === tour.length - 1 ? "Finish tour" : "Next step"}
              <ArrowRight size={15} />
            </button>
            <button
              className="quiet"
              onClick={() => setPortfolio({ tour: -1 })}
            >
              Close tour
            </button>
          </div>
        </section>
      ) : null}
      <main id="main-content" tabIndex={-1}>
        {state.ready ? (
          children
        ) : (
          <p role="status">Preparing your workspace…</p>
        )}
      </main>
      <footer>
        <Radio size={14} />
        <span>Inspectable evidence. Bounded telemetry. Honest outcomes.</span>
        <Link href="/workflow">SDK, setup & evidence →</Link>
      </footer>
    </div>
  );
}

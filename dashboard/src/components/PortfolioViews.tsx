"use client";
import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import {
  ArrowRight,
  CheckCircle2,
  CircleAlert,
  Clock3,
  Play,
  Radio,
  ShieldCheck,
} from "lucide-react";
import type {
  CostSummary,
  ReplayData,
  Run,
  RunDiff,
  RunListResponse,
  TraceResponse,
} from "@/types";
import { readApi, streamTraces } from "@/lib/api";
import { sampleCohort, scenarios } from "@/lib/demo-scenarios";
import {
  getPortfolioState,
  setPortfolio,
  usePortfolio,
} from "@/lib/portfolio-state";
import { useData } from "@/lib/use-data";

export function Status({ value }: { value: string }) {
  return (
    <span className={`outcome ${value}`}>
      <span />
      {value}
    </span>
  );
}
export function ReadState({
  loading,
  error,
  retry,
}: {
  loading: boolean;
  error: string | null;
  retry: () => void;
}) {
  return loading ? (
    <div className="empty" role="status">
      Loading recorded evidence…
    </div>
  ) : error ? (
    <section className="error-box" role="alert">
      <CircleAlert size={23} />
      <div>
        <h3>Collector connection unavailable</h3>
        <p>{error}</p>
        <p>
          Your data source has not changed. Retry the collector or explicitly
          enter the sample experience.
        </p>
        <div className="button-row">
          <button onClick={retry}>Retry</button>
          <button onClick={() => setPortfolio({ source: "sample", tour: -1 })}>
            Enter sample mode
          </button>
        </div>
      </div>
    </section>
  ) : null;
}
function Json({ value }: { value: unknown }) {
  return (
    <pre>{JSON.stringify(value, null, 2) ?? "Unknown / not recorded"}</pre>
  );
}
function Money({ value }: { value: number }) {
  return <>${value.toFixed(5)}</>;
}
function meta(run: Run, key: string) {
  return String(run.metadata?.[key] ?? "unknown");
}

type Execution = {
  id: string;
  scenario: string;
  status: string;
  cohort_id: string;
  progress: { completed: number; total: number };
  run_ids: string[];
  application_outcomes: Record<string, number> | null;
  delivery: Record<string, unknown> | null;
  error: string | null;
};
type Readiness = {
  enabled: boolean;
  ready: boolean;
  reason: string | null;
  scenarios: Array<{ id: string; name: string; description: string }>;
};
export function WorkloadLauncher() {
  const state = usePortfolio();
  const readiness = useData<Readiness>(
    state.source === "connected" ? "/api/portfolio/scenarios" : null,
  );
  const [scenario, setScenario] = useState("incident");
  const [job, setJob] = useState<Execution | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [launching, setLaunching] = useState(false);
  const [jobId, setJobId] = useState<string | null>(null);
  const [statusRetry, setStatusRetry] = useState(0);
  const [errorOrigin, setErrorOrigin] = useState<"launch" | "status">("launch");
  const request = useRef<string | null>(null);
  const launchController = useRef<AbortController | null>(null);
  const selectCompletedCohort = useRef(false);
  useEffect(() => {
    setLaunching(false);
    selectCompletedCohort.current = false;
    if (state.source !== "connected") {
      setJob(null);
      setJobId(null);
      setError(null);
      return;
    }
    setJobId(sessionStorage.getItem("agenttrace.execution.v1"));
    return () => launchController.current?.abort();
  }, [state.source]);
  useEffect(() => {
    if (!jobId || state.source !== "connected") return;
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout>;
    let selected = false;
    const poll = async () => {
      try {
        const next = await readApi<Execution>(
          `/api/portfolio/executions/${jobId}`,
          { signal: controller.signal },
        );
        if (controller.signal.aborted) return;
        setJob(next);
        setError(null);
        if (["queued", "running"].includes(next.status)) {
          selectCompletedCohort.current = true;
          timer = setTimeout(poll, 800);
        } else if (
          next.cohort_id &&
          !selected &&
          selectCompletedCohort.current
        ) {
          selected = true;
          selectCompletedCohort.current = false;
          const current = getPortfolioState();
          setPortfolio({
            cohort: next.cohort_id,
            cohorts: [...new Set([...current.cohorts, next.cohort_id])],
          });
        }
      } catch (err) {
        if (!controller.signal.aborted) {
          setErrorOrigin("status");
          setError(
            err instanceof Error ? err.message : "Execution status unavailable",
          );
        }
      }
    };
    void poll();
    return () => {
      controller.abort();
      clearTimeout(timer);
    };
  }, [jobId, state.source, statusRetry]);
  async function launch(retry = false) {
    launchController.current?.abort();
    const controller = new AbortController();
    launchController.current = controller;
    selectCompletedCohort.current = true;
    setLaunching(true);
    setError(null);
    setErrorOrigin("launch");
    if (!retry || !request.current) request.current = crypto.randomUUID();
    try {
      const created = await readApi<Execution>("/api/portfolio/executions", {
        method: "POST",
        body: JSON.stringify({ scenario, request_id: request.current }),
        signal: controller.signal,
      });
      if (
        controller.signal.aborted ||
        getPortfolioState().source !== "connected"
      )
        return;
      setJob(created);
      setJobId(created.id);
      sessionStorage.setItem("agenttrace.execution.v1", created.id);
    } catch (err) {
      if (!controller.signal.aborted)
        setError(err instanceof Error ? err.message : "Launch failed");
    } finally {
      if (!controller.signal.aborted) setLaunching(false);
    }
  }
  if (state.source !== "connected") return null;
  const active =
    launching || (!!job && ["queued", "running"].includes(job.status));
  return (
    <section className="panel launcher">
      <div className="section-heading">
        <div>
          <small>ACTUAL LOCAL WORKFLOW</small>
          <h2>Run bundled workload</h2>
          <p>
            Twenty overlapping requests. One tracer. Real HTTP export and SQLite
            persistence.
          </p>
        </div>
        <ShieldCheck size={28} />
      </div>
      <p className="subtle">
        Provider responses, token counts and prices are synthetic. Expected
        application errors are separate from telemetry delivery.
      </p>
      <div className="button-row">
        <label>
          Workload scenario
          <select
            aria-label="Workload scenario"
            value={scenario}
            disabled={active}
            onChange={(event) => {
              setScenario(event.target.value);
              request.current = null;
            }}
          >
            {scenarios.map((s) => (
              <option value={s.id} key={s.id}>
                {s.name}
              </option>
            ))}
          </select>
        </label>
        <button
          className="primary"
          disabled={active || !readiness.data?.ready}
          onClick={() => void launch()}
        >
          <Play size={15} />
          {launching ? "Launching…" : "Run bundled workload"}
        </button>
        <button onClick={readiness.retry} className="quiet">
          Refresh availability
        </button>
      </div>
      {readiness.loading ? (
        <p role="status">Checking launcher availability…</p>
      ) : null}
      {readiness.error ? (
        <ReadState
          loading={false}
          error={readiness.error}
          retry={readiness.retry}
        />
      ) : null}
      {readiness.data && !readiness.data.ready ? (
        <p className="notice">
          {readiness.data.reason ||
            "Launcher is disabled. Enable PORTFOLIO_LAUNCH_ENABLED and install the SDK on the local collector."}
        </p>
      ) : null}
      {error ? (
        <div className="error-box" role="alert">
          <div>
            <p>{error}</p>
            <button
              onClick={() => {
                if (jobId) {
                  if (errorOrigin === "status")
                    setStatusRetry((value) => value + 1);
                  else void launch(true);
                } else void launch(true);
              }}
            >
              Retry last request
            </button>
          </div>
        </div>
      ) : null}
      {job ? (
        <div
          className="execution-status"
          data-testid="execution-status"
          role="status"
        >
          <div className="section-heading">
            <strong>Execution {job.status}</strong>
            <span>
              {job.progress.completed}/{job.progress.total} requests
            </span>
          </div>
          <progress value={job.progress.completed} max={job.progress.total} />
          <p>
            <code>{job.cohort_id}</code>
          </p>
          {job.application_outcomes ? (
            <p>
              Application outcomes:{" "}
              {Object.entries(job.application_outcomes)
                .map(([key, value]) => `${value} ${key}`)
                .join(" · ")}
            </p>
          ) : null}
          {job.delivery ? (
            <p>
              Telemetry:{" "}
              {job.delivery.complete === true
                ? "complete delivery confirmed"
                : "delivery incomplete or unconfirmed"}{" "}
              · {String(job.delivery.delivered ?? "unknown")} delivered ·{" "}
              {String(job.delivery.dropped ?? "unknown")} dropped ·{" "}
              {String(job.delivery.unfinished ?? "unknown")} unfinished
            </p>
          ) : null}
          {job.error ? <p className="danger-text">{job.error}</p> : null}
          {job.status === "interrupted" ? (
            <p>
              Collector restarted before this execution finished. Partial traces
              remain available. Explicitly launch again to create a new cohort.
            </p>
          ) : null}
          <details>
            <summary>Execution and delivery evidence</summary>
            <Json value={job} />
          </details>
        </div>
      ) : null}
    </section>
  );
}

function MetricCards({ runs }: { runs: Run[] }) {
  const completed = runs.filter((run) => run.status === "completed").length;
  const failed = runs.filter((run) => run.status === "failed").length;
  const cancelled = runs.filter((run) => run.status === "cancelled").length;
  return (
    <div className="metric-grid">
      <div>
        <small>RECORDED REQUESTS</small>
        <strong data-testid="run-count">{runs.length}</strong>
        <span>Selected cohort / history page</span>
      </div>
      <div>
        <small>COMPLETED</small>
        <strong className="success-text" data-testid="completed-count">
          {completed}
        </strong>
        <span>Reached a terminal success</span>
      </div>
      <div>
        <small>FAILED</small>
        <strong className="danger-text" data-testid="failed-count">
          {failed}
        </strong>
        <span>Investigate the exact stage</span>
      </div>
      <div>
        <small>CANCELLED</small>
        <strong>{cancelled}</strong>
        <span>Caller stopped the request</span>
      </div>
    </div>
  );
}
export function RunRows({ runs }: { runs: Run[] }) {
  return (
    <div className="run-list">
      {runs.map((run) => (
        <Link
          data-testid="run-row"
          href={`/runs/${run.id}`}
          key={run.id}
          className="run-row"
        >
          <span className="run-ident">
            <strong>{run.name}</strong>
            <small>{run.correlation_id ?? "Correlation unknown"}</small>
          </span>
          <Status value={run.status} />
          <span>{run.span_count} spans</span>
          <span className="mono">
            <Money value={run.total_cost} />
          </span>
          <ArrowRight size={16} />
        </Link>
      ))}
    </div>
  );
}
export function RequestLanes({ runs }: { runs: Run[] }) {
  if (!runs.length) return null;
  const base = Math.min(...runs.map((run) => Date.parse(run.start_time)));
  const max = Math.max(
    1,
    ...runs.map((run) => Date.parse(run.end_time ?? run.start_time) - base),
  );
  return (
    <section className="panel">
      <div className="section-heading">
        <div>
          <small>CONCURRENT REQUEST LANES</small>
          <h2>Separate traces. Shared time.</h2>
        </div>
        <span className="eyebrow">Select a request →</span>
      </div>
      <p>
        Each lane is one recorded request. Position and length use recorded
        timestamps; colors also have text labels.
      </p>
      <div className="lanes">
        {runs.map((run) => {
          const left = Math.max(
            0,
            ((Date.parse(run.start_time) - base) / max) * 100,
          );
          const width = Math.max(
            5,
            ((Date.parse(run.end_time ?? run.start_time) -
              Date.parse(run.start_time)) /
              max) *
              100,
          );
          return (
            <Link
              href={`/runs/${run.id}`}
              key={run.id}
              className="lane"
              aria-label={`${run.name}, ${run.status}`}
            >
              <span>{run.name}</span>
              <span className="lane-track">
                <span
                  className={`lane-bar ${run.status}`}
                  style={{ left: `${left}%`, width: `${width}%` }}
                />
              </span>
              <Status value={run.status} />
            </Link>
          );
        })}
      </div>
    </section>
  );
}

export function OverviewView() {
  const state = usePortfolio();
  const router = useRouter();
  const result = useData<RunListResponse>("/api/runs?limit=100", true);
  const runs = result.data?.runs ?? [];
  const failed = runs.find((run) => run.status === "failed");
  return (
    <>
      <section className="hero">
        <div>
          <div className="eyebrow">
            <span className="live-dot" />
            PROJECT 04 / AGENTTRACE
          </div>
          <h1>
            Find the failing step in an AI workflow, even when requests overlap.
          </h1>
          <p>
            Follow a request from retrieval to response. Inspect its evidence,
            understand the failure, and see precisely what the repair changed.
          </p>
          <div className="button-row">
            <button
              className="primary"
              onClick={() => {
                if (state.source === "sample") {
                  setPortfolio({ tour: 0, scenario: "incident" });
                  router.push("/runs");
                } else router.push(failed ? `/runs/${failed.id}` : "/runs");
              }}
            >
              Investigate a failure
              <ArrowRight size={16} />
            </button>
            <Link className="button" href="/runs">
              Explore traces
            </Link>
          </div>
        </div>
        <div className="hero-proof">
          <ActivityMini />
          <span>REQUEST → RETRIEVAL → PROVIDER → RESPONSE</span>
          <strong>
            Know where.
            <br />
            Understand why.
          </strong>
          <p>
            One correlation per request.
            <br />
            Safe summaries by default.
            <br />
            Failures stay visible.
          </p>
        </div>
      </section>
      <WorkloadLauncher />
      <ReadState
        loading={result.loading}
        error={result.error}
        retry={result.retry}
      />
      {result.data ? (
        <>
          <MetricCards runs={runs} />
          {runs.length ? (
            <>
              <RequestLanes runs={runs} />
              <section className="panel">
                <div className="section-heading">
                  <h2>Start with the unexpected outcomes</h2>
                  <Link href="/runs">All requests →</Link>
                </div>
                <RunRows
                  runs={[
                    ...runs.filter((run) => run.status !== "completed"),
                    ...runs
                      .filter((run) => run.status === "completed")
                      .slice(0, 2),
                  ]}
                />
              </section>
            </>
          ) : (
            <section className="empty">
              <h2>No recorded requests yet</h2>
              <p>
                Launch the bundled workload above or connect your independently
                installed SDK.
              </p>
              <Link href="/workflow">Actual project quick start →</Link>
            </section>
          )}
        </>
      ) : null}
    </>
  );
}
function ActivityMini() {
  return (
    <div className="mini-trace" aria-hidden="true">
      {[0, 1, 2, 3, 4].map((index) => (
        <div key={index}>
          <i
            style={{ width: `${55 + index * 7}%`, marginLeft: `${index * 4}%` }}
          />
          <i
            className={index === 3 ? "fault" : ""}
            style={{ width: `${15 + index * 3}%` }}
          />
        </div>
      ))}
    </div>
  );
}

export function RunsView() {
  const state = usePortfolio();
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [offset, setOffset] = useState(0);
  useEffect(() => setOffset(0), [state.source, state.cohort, state.scenario]);
  const result = useData<RunListResponse>(
    `/api/runs?limit=100&offset=${offset}${status ? `&status=${status}` : ""}${search ? `&search=${encodeURIComponent(search)}` : ""}`,
    true,
  );
  const all = useData<RunListResponse>("/api/runs?limit=100", true);
  return (
    <>
      <div className="page-heading">
        <small>INVESTIGATE</small>
        <h1>Runs</h1>
        <p>
          Every request keeps its own outcome and correlation. Select one to
          inspect the steps.
        </p>
      </div>
      {all.data ? <MetricCards runs={all.data.runs} /> : null}
      <section className="panel">
        <div className="filters">
          <label>
            Search runs
            <input
              placeholder="Search runs..."
              value={search}
              onChange={(event) => {
                setSearch(event.target.value);
                setOffset(0);
              }}
            />
          </label>
          <div className="filter-buttons" role="group" aria-label="Run status">
            {["", "completed", "failed", "cancelled", "running"].map(
              (value) => (
                <button
                  aria-pressed={status === value}
                  className={status === value ? "selected" : ""}
                  key={value}
                  onClick={() => {
                    setStatus(value);
                    setOffset(0);
                  }}
                >
                  {value || "All outcomes"}
                </button>
              ),
            )}
          </div>
        </div>
        <ReadState
          loading={result.loading}
          error={result.error}
          retry={result.retry}
        />
        {result.data ? (
          <>
            <p className="subtle">
              Showing {result.data.total ? offset + 1 : 0}–
              {offset + result.data.runs.length} of {result.data.total} matching
              requests
            </p>
            {result.data.runs.length ? (
              <RunRows runs={result.data.runs} />
            ) : (
              <p className="empty">No requests match these filters.</p>
            )}
            {result.data.total > 100 ? (
              <div className="button-row">
                <button
                  disabled={offset === 0}
                  onClick={() => setOffset((value) => Math.max(0, value - 100))}
                >
                  Previous page
                </button>
                <button
                  disabled={
                    offset + result.data.runs.length >= result.data.total
                  }
                  onClick={() => setOffset((value) => value + 100)}
                >
                  Next page
                </button>
              </div>
            ) : null}
          </>
        ) : null}
      </section>
      {all.data ? <RequestLanes runs={all.data.runs} /> : null}
    </>
  );
}

function SpanInvestigation({
  run,
  spans,
}: {
  run: Run;
  spans: TraceResponse[];
}) {
  const [selected, setSelected] = useState<string | null>(null);
  const ordered = [...spans].sort((a, b) =>
    a.start_time.localeCompare(b.start_time),
  );
  const current =
    ordered.find((span) => span.id === selected) ??
    ordered.find((span) => span.status === "error" || span.error) ??
    ordered[0];
  const start = Math.min(...ordered.map((span) => Date.parse(span.start_time)));
  const end = Math.max(
    start + 1,
    ...ordered.map((span) => Date.parse(span.end_time ?? span.start_time)),
  );
  return (
    <section className="panel">
      <div className="section-heading">
        <div>
          <small>REQUEST → RETRIEVAL → PROVIDER → VALIDATION</small>
          <h2>Request timeline</h2>
        </div>
          <span>
            {spans.length} recorded {spans.length === 1 ? "stage" : "stages"}
          </span>
      </div>
      <p>
        Choose a stage in the waterfall or its equivalent ordered text list.
        Content is summarized unless capture was explicitly enabled.
      </p>
      {!spans.length ? (
        <p className="empty">
          No spans were recorded. Delivery may be incomplete; absence is not
          evidence of successful execution.
        </p>
      ) : (
        <>
          <div className="waterfall" aria-label="Span waterfall">
            {ordered.map((span) => (
              <button
                key={span.id}
                onClick={() => setSelected(span.id)}
                aria-pressed={current?.id === span.id}
                className={`waterfall-row ${span.status}`}
              >
                <span>{span.name}</span>
                <span className="waterfall-track">
                  <span
                    style={{
                      marginLeft: `${((Date.parse(span.start_time) - start) / (end - start)) * 100}%`,
                      width: `${Math.max(3, ((span.duration_ms ?? 0) / (end - start)) * 100)}%`,
                    }}
                  />
                </span>
                <span>{span.duration_ms?.toFixed(1) ?? "?"}ms</span>
              </button>
            ))}
          </div>
          <div className="investigation-grid">
            <ol className="stage-list" aria-label="Ordered text stages">
              {ordered.map((span, index) => (
                <li key={span.id}>
                  <button
                    onClick={() => setSelected(span.id)}
                    aria-pressed={current?.id === span.id}
                  >
                    <span className="stage-number">{index + 1}</span>
                    <span>
                      <strong>{span.name}</strong>
                      <small>
                        {span.span_type} · {span.status} ·{" "}
                        {span.duration_ms?.toFixed(1) ?? "unknown"}ms
                      </small>
                    </span>
                    {span.status === "error" || span.status === "cancelled" ? (
                      <CircleAlert size={16} />
                    ) : (
                      <CheckCircle2 size={16} />
                    )}
                  </button>
                </li>
              ))}
            </ol>
            {current ? (
              <section className="span-inspector" aria-label="Selected span">
                <div className="section-heading">
                  <h3>{current.name}</h3>
                  <Status value={current.status} />
                </div>
                {current.error ? (
                  <div className="notice danger">
                    <strong>What happened</strong>
                    <p>{current.error}</p>
                  </div>
                ) : (
                  <p className="notice">
                    This stage reached its recorded outcome. It does not
                    establish factual quality of a synthetic provider response.
                  </p>
                )}
                <dl className="identity-list">
                  <dt>Correlation</dt>
                  <dd>{run.correlation_id ?? "Unknown"}</dd>
                  <dt>Run</dt>
                  <dd>{run.id}</dd>
                  <dt>Span</dt>
                  <dd>{current.span_id}</dd>
                  <dt>Parent</dt>
                  <dd>{current.parent_span_id ?? "Root span"}</dd>
                  <dt>Attempt</dt>
                  <dd>
                    {String(
                      current.metadata?.attempt ?? "Unknown / historical",
                    )}
                  </dd>
                </dl>
                <details>
                  <summary>Capture summaries, arguments and results</summary>
                  <h4>Input</h4>
                  <Json value={current.input_data} />
                  <h4>Output</h4>
                  <Json value={current.output_data} />
                  <h4>Safe metadata</h4>
                  <Json value={current.metadata} />
                </details>
                <details>
                  <summary>Exact recorded trace</summary>
                  <Json value={current} />
                </details>
              </section>
            ) : null}
          </div>
        </>
      )}
    </section>
  );
}

function Comparison({ run }: { run: Run }) {
  const state = usePortfolio();
  const [other, setOther] = useState(
    state.source === "sample"
      ? run.id.includes("sample-incident-")
        ? run.id.replace("sample-incident-", "sample-repaired-")
        : run.id.replace("sample-repaired-", "sample-incident-")
      : "",
  );
  const choices = useData<RunListResponse>(
    state.source === "connected" ? "/api/runs?limit=100" : null,
  );
  const result = useData<RunDiff>(
    other
      ? `/api/diff/runs?run_id_1=${encodeURIComponent(run.id)}&run_id_2=${encodeURIComponent(other)}`
      : null,
  );
  return (
    <section className="panel">
      <h2>Run comparison</h2>
      <p>
        Stages align by logical identity, occurrence and attempt. A retrieval
        repair does not claim to fix timeout or cancellation.
      </p>
      <label>
        Compare with
        {state.source === "sample" ? (
          <select
            aria-label="Compare with"
            value={other}
            onChange={(event) => setOther(event.target.value)}
          >
            {[
              ...sampleCohort("incident").runs,
              ...sampleCohort("repaired").runs,
            ]
              .filter((row) => row.id !== run.id)
              .map((row) => (
                <option value={row.id} key={row.id}>
                  {row.name} · {String(row.metadata?.scenario)}
                </option>
              ))}
          </select>
        ) : (
          <>
            <input
              aria-label="Compare with"
              placeholder="Run ID from another cohort"
              list="compare-runs"
              value={other}
              onChange={(event) => setOther(event.target.value)}
            />
            <datalist id="compare-runs">
              {choices.data?.runs
                .filter((row) => row.id !== run.id)
                .map((row) => (
                  <option value={row.id} key={row.id}>
                    {row.name} · {meta(row, "scenario")}
                  </option>
                ))}
            </datalist>
          </>
        )}
      </label>
      {!other ? (
        <p className="empty">
          Select runs to compare. Run the repaired scenario, then choose the
          same case from that cohort.
        </p>
      ) : (
        <>
          <ReadState
            loading={result.loading}
            error={result.error}
            retry={result.retry}
          />
          {result.data ? (
            <>
              <p
                className={`notice ${result.data.compatibility?.compatible === false ? "danger" : ""}`}
              >
                {result.data.compatibility?.compatible === true
                  ? "Compatible scenario revision"
                  : result.data.compatibility?.compatible === false
                    ? "Incompatible scenario revisions — no valid repair conclusion"
                    : "Historical scenario revision unknown — comparison is descriptive only"}
                . {result.data.compatibility?.reason}
              </p>
              <div className="comparison-head">
                <div>
                  <small>ORIGINAL</small>
                  <h3>{result.data.run1.name}</h3>
                  <Status value={result.data.run1.status} />
                </div>
                <ArrowRight />
                <div>
                  <small>CANDIDATE</small>
                  <h3>{result.data.run2.name}</h3>
                  <Status value={result.data.run2.status} />
                </div>
              </div>
              <div className="table-scroll">
                <table>
                  <thead>
                    <tr>
                      <th>Logical stage</th>
                      <th>Occurrence / attempt</th>
                      <th>Original</th>
                      <th>Candidate</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.data.aligned_stages?.map((stage, index) => (
                      <tr key={`${stage.stage_key}-${index}`}>
                        <td>{stage.name || stage.stage_key}</td>
                        <td>
                          {stage.occurrence} / {stage.attempt}
                        </td>
                        <td>{stage.status_1 ?? "Unmatched"}</td>
                        <td>
                          {stage.status_2 ?? "Unmatched"}
                          {stage.status_changed ? " · changed" : ""}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {!result.data.aligned_stages ? (
                <p className="notice">
                  Legacy comparison has no occurrence alignment evidence.
                </p>
              ) : null}
              <details>
                <summary>
                  Complete comparison evidence and unmatched stages
                </summary>
                <Json value={result.data} />
              </details>
            </>
          ) : null}
        </>
      )}
    </section>
  );
}

function Playback({ runId }: { runId: string }) {
  const state = usePortfolio();
  const result = useData<ReplayData>(`/api/replay/runs/${runId}`);
  const [step, setStep] = useState(0);
  const [playing, setPlaying] = useState(false);
  useEffect(() => {
    setPlaying(false);
    setStep(0);
  }, [runId, state.source, state.scenario]);
  useEffect(() => {
    if (!playing) return;
    const timer = setInterval(
      () =>
        setStep((current) => {
          if (current + 1 >= (result.data?.steps.length ?? 0)) {
            setPlaying(false);
            return current;
          }
          return current + 1;
        }),
      1000,
    );
    return () => clearInterval(timer);
  }, [playing, result.data]);
  return (
    <section className="panel">
      <h2>Recorded playback</h2>
      <p>
        Inspect saved steps in fixed order. These controls do not execute tools
        or call providers.
      </p>
      <ReadState
        loading={result.loading}
        error={result.error}
        retry={result.retry}
      />
      {result.data ? (
        <>
          <div className="button-row">
            <button
              disabled={step === 0}
              onClick={() => setStep((value) => value - 1)}
            >
              Previous step
            </button>
            <button onClick={() => setPlaying(!playing)}>
              {playing ? "Pause" : "Play"}
            </button>
            <button
              disabled={step >= result.data.steps.length - 1}
              onClick={() => setStep((value) => value + 1)}
            >
              Next step
            </button>
            <span>
              Step {result.data.steps.length ? step + 1 : 0} of{" "}
              {result.data.steps.length}
            </span>
          </div>
          {result.data.steps[step] ? (
            <>
              <h3>{result.data.steps[step].name}</h3>
              <Json value={result.data.steps[step]} />
            </>
          ) : (
            <p>No saved steps.</p>
          )}
        </>
      ) : null}
    </section>
  );
}

export function RunDetailView() {
  const params = useParams<{ id: string }>();
  const state = usePortfolio();
  const [tab, setTab] = useState("timeline");
  const run = useData<Run>(`/api/runs/${params.id}`);
  const spans = useData<TraceResponse[]>(`/api/runs/${params.id}/spans`);
  useEffect(() => {
    setTab("timeline");
  }, [params.id, state.source]);
  return (
    <>
      <Link className="back-link" href="/runs">
        ← All runs
      </Link>
      <ReadState loading={run.loading} error={run.error} retry={run.retry} />
      {run.data ? (
        <>
          <div className="page-heading">
            <small>REQUEST INVESTIGATION</small>
            <h1>{run.data.name}</h1>
            <Status value={run.data.status} />
            <p className="mono">{run.data.id}</p>
            <p>
              Scenario: {meta(run.data, "scenario")} · Case:{" "}
              {meta(run.data, "case_id")} · Pricing:{" "}
              {meta(run.data, "pricing_origin")}
            </p>
            {state.source === "connected" &&
            typeof run.data.metadata?.cohort_id === "string" &&
            run.data.metadata.cohort_id !== state.cohort ? (
              <button
                onClick={() => {
                  const cohort = String(run.data!.metadata!.cohort_id);
                  setPortfolio({
                    cohort,
                    cohorts: [...new Set([...state.cohorts, cohort])],
                  });
                }}
              >
                Use this run&apos;s cohort
              </button>
            ) : null}
          </div>
          <div className="tabs" role="group" aria-label="Run inspection">
            {[
              { id: "timeline", name: "Timeline" },
              { id: "compare", name: "Compare repair" },
              { id: "playback", name: "Recorded playback" },
            ].map((item) => (
              <button
                key={item.id}
                aria-pressed={tab === item.id}
                onClick={() => setTab(item.id)}
              >
                {item.name}
              </button>
            ))}
          </div>
          {tab === "timeline" ? (
            <>
              <ReadState
                loading={spans.loading}
                error={spans.error}
                retry={spans.retry}
              />
              {spans.data ? (
                <SpanInvestigation
                  key={run.data.id}
                  run={run.data}
                  spans={spans.data}
                />
              ) : null}
            </>
          ) : tab === "compare" ? (
            <Comparison key={run.data.id} run={run.data} />
          ) : (
            <Playback runId={run.data.id} />
          )}
          <details className="panel">
            <summary>Run identity, provenance and safe metadata</summary>
            <Json value={run.data} />
          </details>
        </>
      ) : null}
    </>
  );
}

export function CostsView() {
  const state = usePortfolio();
  const result = useData<CostSummary>("/api/costs/summary", true);
  const runs = useData<RunListResponse>("/api/runs?limit=100", true);
  const origins = [
    ...new Set(runs.data?.runs.map((run) => meta(run, "pricing_origin")) ?? []),
  ];
  return (
    <>
      <div className="page-heading">
        <small>ATTRIBUTION</small>
        <h1>Costs</h1>
        <p>
          The same selected cohort, attributed by provider and model. Token
          usage and prices in the bundled workload are synthetic.
        </p>
      </div>
      <ReadState
        loading={result.loading}
        error={result.error}
        retry={result.retry}
      />
      {result.data ? (
        <>
          <div className="metric-grid">
            <div>
              <small>RECORDED ESTIMATE</small>
              <strong>
                <Money value={result.data.total_cost} />
              </strong>
              <span>Not an invoice or provider billing evidence</span>
            </div>
            <div>
              <small>TOKENS</small>
              <strong>{result.data.total_tokens.toLocaleString()}</strong>
              <span>Bundled workload: synthetic</span>
            </div>
            <div>
              <small>SPANS</small>
              <strong>{result.data.total_spans}</strong>
              <span>Filtered with the selected cohort</span>
            </div>
            <div>
              <small>PRICING PROVENANCE</small>
              <strong className="small-metric">
                {state.source === "sample"
                  ? "Illustrative"
                  : origins.length
                    ? origins.join(", ")
                    : "Unknown"}
              </strong>
              <span>Historical values are not retrospectively verified</span>
            </div>
          </div>
          <section className="panel" data-testid="cost-chart">
            <h2>Where the estimate comes from</h2>
            <div className="two-columns">
              {[
                { name: "Provider", values: result.data.by_provider },
                { name: "Model", values: result.data.by_model },
              ].map((group) => (
                <div key={group.name}>
                  <h3>{group.name}</h3>
                  {Object.entries(group.values).length ? (
                    Object.entries(group.values).map(([key, value]) => (
                      <div className="cost-row" key={key}>
                        <span>{key}</span>
                        <strong>
                          <Money value={value} />
                        </strong>
                        <progress
                          max={Math.max(result.data!.total_cost, 0.00001)}
                          value={value}
                        />
                      </div>
                    ))
                  ) : (
                    <p>Attribution unknown / not recorded.</p>
                  )}
                </div>
              ))}
            </div>
            <details>
              <summary>Exact aggregate response</summary>
              <Json value={result.data} />
            </details>
          </section>
        </>
      ) : null}
    </>
  );
}

export function LiveView() {
  const state = usePortfolio();
  const [events, setEvents] = useState<TraceResponse[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [paused, setPaused] = useState(true);
  const [index, setIndex] = useState(0);
  const [retry, setRetry] = useState(0);
  const cursor = useRef("");
  const pool = sampleCohort(state.scenario).events;
  useEffect(() => {
    setEvents([]);
    setIndex(0);
    setError(null);
    cursor.current = "";
    setPaused(
      state.source === "sample"
        ? window.matchMedia("(prefers-reduced-motion: reduce)").matches
        : false,
    );
  }, [state.source, state.scenario, state.cohort, state.version]);
  useEffect(() => {
    if (state.source !== "sample" || paused) return;
    const timer = setInterval(
      () => setIndex((value) => Math.min(value + 1, pool.length)),
      600,
    );
    return () => clearInterval(timer);
  }, [state.source, paused, pool.length]);
  useEffect(() => {
    if (state.source !== "connected" || paused) return;
    return streamTraces(
      (trace) => {
        if (trace.delivery_cursor)
          cursor.current = String(trace.delivery_cursor);
        setEvents((previous) =>
          previous.some((row) => row.id === trace.id)
            ? previous
            : [...previous, trace].slice(-100),
        );
      },
      {
        cohort: state.cohort,
        cursor: cursor.current,
        onOpen: () => setError(null),
        onError: setError,
      },
    );
  }, [state.source, state.cohort, paused, retry]);
  const shown = state.source === "sample" ? pool.slice(0, index) : events;
  return (
    <>
      <div className="page-heading">
        <small>
          {state.source === "sample"
            ? "DETERMINISTIC SAMPLE PLAYBACK"
            : "COLLECTOR EVENT STREAM"}
        </small>
        <h1>{state.source === "sample" ? "Recorded playback" : "Live"}</h1>
        <p>
          {state.source === "sample"
            ? "Reveal fixed events in order. No network stream or provider execution is involved. Reduced motion starts in manual step mode."
            : "Actual persisted collector events, resumed with a durable ingestion cursor. Display history is bounded to 100 events."}
        </p>
      </div>
      <section className="panel">
        <div className="button-row">
          <button onClick={() => setPaused(!paused)}>
            <Radio size={16} />
            {paused ? "Play / resume" : "Pause"}
          </button>
          {state.source === "sample" ? (
            <>
              <button
                onClick={() => {
                  setPaused(true);
                  setIndex((value) => Math.min(value + 1, pool.length));
                }}
              >
                Step event
              </button>
              <button
                onClick={() => {
                  setPaused(true);
                  setIndex(0);
                }}
              >
                Reset playback
              </button>
            </>
          ) : (
            <button
              onClick={() => {
                setRetry((value) => value + 1);
                setPaused(false);
              }}
            >
              Retry stream
            </button>
          )}
          <span role="status">
            {shown.length} events shown
            {state.source === "sample"
              ? ` / ${pool.length}`
              : " · bounded to100"}
          </span>
        </div>
        {error ? (
          <div className="error-box" role="alert">
            <div>
              <p>{error}</p>
              <p>
                Connected mode stays connected. Retry or explicitly select
                sample data.
              </p>
              <button
                onClick={() => {
                  setRetry((value) => value + 1);
                  setPaused(false);
                }}
              >
                Retry
              </button>
            </div>
          </div>
        ) : null}
        {shown.length ? (
          <ol className="event-list">
            {shown.map((event, i) => (
              <li
                key={event.id}
                data-delivery-cursor={event.delivery_cursor}
                data-run-id={event.run_id}
              >
                <span className="event-index">{i + 1}</span>
                <div>
                  <Link href={`/runs/${event.run_id}`}>{event.name}</Link>
                  <small>
                    {event.run_id} · {event.span_type}
                  </small>
                </div>
                <Status value={event.status} />
                <details>
                  <summary>Event</summary>
                  <Json value={event} />
                </details>
              </li>
            ))}
          </ol>
        ) : (
          <p className="empty">
            {state.source === "sample"
              ? "Press Step event or Play to inspect the first recorded event."
              : "Waiting for spans. Launch a workload in Overview while this collector is running."}
          </p>
        )}
      </section>
    </>
  );
}

export function WorkflowView() {
  return (
    <>
      <div className="page-heading">
        <small>REPRODUCE THE EVIDENCE</small>
        <h1>The actual project workflow</h1>
        <p>
          The SDK is independently installable and has no mandatory
          dependencies. The local collector and dashboard provide persistence
          and investigation.
        </p>
      </div>
      <section className="panel">
        <h2>From code to an inspectable incident</h2>
        <ol className="workflow-steps">
          <li>
            <strong>Install the SDK and optional collector</strong>
            <p>
              Use an isolated Python3.11+ environment. Installing the collector
              is separate from installing the SDK.
            </p>
            <pre>
              {
                'python -m pip install ./sdk\npython -m pip install "./server[dev]"'
              }
            </pre>
          </li>
          <li>
            <strong>Run the local collector explicitly</strong>
            <p>
              Use loopback binding, a dedicated SQLite file, explicit browser
              origins and the documented launcher configuration.
            </p>
            <pre>
              {
                'PORTFOLIO_LAUNCH_ENABLED=true\nDATABASE_URL=sqlite+aiosqlite:///./data/review.db\nCORS_ORIGINS=["http://localhost:3404"]\nuvicorn app.main:app --host 127.0.0.1 --port 8300'
              }
            </pre>
            <p>
              Set environment variables using your shell; the lines above
              describe configuration values. The local credential-free workflow
              does not establish hosted authentication readiness.
            </p>
          </li>
          <li>
            <strong>
              Run the same bundled workload through CLI or dashboard
            </strong>
            <pre>
              {
                "python -m agenttrace.portfolio --scenario incident --endpoint http://127.0.0.1:8300 --output incident.json\npython -m agenttrace.portfolio --scenario repaired --endpoint http://127.0.0.1:8300 --output repaired.json"
              }
            </pre>
            <p>
              Or choose Connected collector and explicitly click Run bundled
              workload. Each launch creates a new cohort and real request/span
              identifiers.
            </p>
          </li>
          <li>
            <strong>Inspect delivery, then diagnose</strong>
            <p>
              Check dropped, failed and unfinished telemetry before claiming
              complete delivery. Compare the same case across incident and
              repaired cohorts. Playback only reads stored evidence.
            </p>
          </li>
        </ol>
      </section>
      <section className="panel">
        <h2>Engineering boundaries and evidence</h2>
        <div className="evidence-grid">
          <article>
            <ShieldCheck />
            <h3>Context isolation</h3>
            <p>
              Independent request contexts, inherited child spans and root
              finalization are verified separately from synthetic model
              responses.
            </p>
          </article>
          <article>
            <Clock3 />
            <h3>Bounded delivery</h3>
            <p>
              Finite queues, retry limits, redaction and deadline results keep
              telemetry failures visible without replacing application results.
            </p>
          </article>
          <article>
            <CheckCircle2 />
            <h3>Honest provenance</h3>
            <p>
              Provider output, usage and prices are illustrative. Real
              concurrency, HTTP delivery, storage and browser behavior have
              separate evidence.
            </p>
          </article>
        </div>
        <div className="button-row">
          <a href="/evidence/portfolio-connected.md">
            Local setup and architecture
          </a>
          <a href="/evidence/portfolio-verification.md">Verification record</a>
          <a href="/evidence/portfolio-case-study.md">Technical case study</a>
        </div>
        <p className="subtle">
          These documents are included with this local dashboard. Repository
          source: portfolio/agenttrace; documentation:
          docs/portfolio-connected.md, docs/portfolio-verification.md and
          docs/portfolio-case-study.md.
        </p>
      </section>
    </>
  );
}

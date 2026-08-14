# Replay

Replay is a read-only view over captured spans. The SDK records inputs, outputs,
tool and model metadata, timing, token usage, and cost. The server loads spans
for a run in `start_time` order; the dashboard renders the timeline and the
replay endpoint exposes the same ordered data for scripts.

```text
POST /api/traces -> stored run/spans -> GET /api/replay/runs/{run_id}
                                      -> dashboard step-through timeline
```

Replay supports waterfall inspection, cumulative cost/token display, error
highlighting, and deterministic run diffing. It does not re-execute prompts or
tools, roll back external side effects, or reconstruct program state that was
not captured. A rerun against a live provider can produce different output and
must be treated as a new run.

The portfolio evidence scenario includes replay-shaped canonical output so a
reviewer can inspect the data contract without running a provider.

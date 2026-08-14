# Deterministic sampling

Sampling is disabled by default (`TRACE_SAMPLING_MODE=off`), which keeps every
trace in local development. `head` and `tail` modes use a score derived from
the first eight bytes of `sha256(trace_id)`, so the same trace ID receives the
same decision across processes and Python versions.

| Setting | Meaning |
| --- | --- |
| `TRACE_SAMPLING_MODE` | `off`, `head`, or `tail` |
| `TRACE_SAMPLE_RATE` | Stable retention rate from `0.0` to `1.0` |
| `TRACE_TAIL_KEEP_ERRORS` | Keep terminal error/failed traces |
| `TRACE_TAIL_SLOW_MS` | Keep terminal spans at or above this duration |

Tail mode buffers a run until a terminal status (`completed`, `complete`,
`error`, or `failed`) is observed. The terminal error/slow override or stable
rate decision is then applied to the complete buffered run. Incomplete runs can
be flushed explicitly and default to a deterministic discard disposition. The
buffer is in-process by design; hosted coordination remains deferred.

Responses add `sampled` and `sampling_reason` without removing existing trace
fields. Timing and buffer state are not part of the portfolio evidence hash.

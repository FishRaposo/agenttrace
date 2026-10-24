# When overlapping AI requests hide the failing stage

AgentTrace's strongest proof is a repaired observability boundary and a usable
investigation of its evidence. This is a local engineering case, not a customer
testimonial, production incident or claim of provider/model quality.

## The reproduced defect

At base `c721c3f`, two asyncio requests shared one tracer. The second raised
`A run is already in progress`. ContextVars held identifiers, but the tracer
still owned one mutable active run and span stack. Identifiers alone did not
isolate the execution state they described.

Fresh baseline gates passed 132 SDK and 98 collector tests. New behavioral
regressions exposed two/twenty-way isolation, child/thread ownership, enclosing
context restoration, cancellation and late-span problems. This explains why
passing existing tests did not establish the missing concurrency contract.

## Engineering repair

Per-tracer ContextVars own the root, immutable stack and frozen sampling decision.
Root aggregation is protected while inherited child tasks and explicitly
propagated thread contexts contribute. Closing the root rejects late spans and
finalizes unfinished work. Terminal errors/cancellation cannot become completed
when a context manager exits. Separate tracer instances restore their enclosing
context.

Lifecycle ASGI instrumentation keeps the request open through streamed body
completion or disconnect/cancellation. The dependency-free SDK imports without
FastAPI; actual optional integration tests run in a separate equipped environment.

Exporting must not make an application result depend on telemetry availability.
A finite background queue takes sanitized snapshots, drops newest on saturation
and exposes failures/unfinished work. Deadline-aware close cannot kill an
arbitrary executing Python exporter, so it returns honest unfinished counts.
That limitation is part of the interface, not a hidden delivery guarantee.

## The end-to-end check found more than unit tests

The first actual SDK→HTTP→SQLite inspection caught a run reporting two spans
when playback and SQL contained one. A terminal root summary arrived before its
buffered span: its producer count was seeded and then incremented again. The
repair reconciles aggregates against stored spans and preserves terminal state.
The same real HTTP proof then passed with 56 incident and 58 repaired spans.

Benchmark traffic subsequently exposed a run-creation uniqueness race. The
verification record distinguishes that initial observation from the final
post-repair measurements. Neither a successful launch response nor an empty
export queue alone certifies complete stored telemetry.

Other recorded regressions cover credential/content leakage through wrapper
metadata, source-preserving OTLP JSON redaction, duplicate span delivery, delayed
run-start updates, repeated-stage comparisons and late-arriving live events.
Original golden evidence remains a separate unchanged contract.

## A reviewable incident

The bundled application runs twenty actual overlapping tasks using one tracer.
Incident has 17 completed requests, a retrieval failure, a provider timeout and a
cancellation. Repaired has 18 completed requests; only retrieval changes. Stable
case/stage keys permit comparison, while actual run/span/cohort IDs stay unique.
Answers, token usage and pricing are explicitly synthetic/illustrative.

The recruiter preview starts populated and guides the same investigation with
fixed local fixtures. The connected dashboard explicitly launches the actual
workload and inspects persisted results. Costs and live events follow the chosen
cohort. Connected errors stay errors; sample playback is labeled separately and
requires no backend/provider/font connection.

## What this supports in an interview

Explain the difference between context-local identifiers and context-local
ownership. Demonstrate a failing stage across concurrent request lanes, then
show how delivery, aggregate reconciliation and a durable ingestion cursor make
that evidence dependable. Discuss queue saturation and shutdown without claiming
that Python can terminate an arbitrary blocked exporter.

This supports a bounded backend/AI-app audit or repair story: reproduce a defect,
protect it with a test, patch the boundary and inspect the actual result. It does
not establish client revenue, production adoption or a universal performance
improvement. [Raw measurement protocol and final gates](portfolio-verification.md)
bound the claim; [actual setup](portfolio-connected.md) lets another developer
repeat it.

# Three-minute AgentTrace review

## Explore the visual preview

1. Select **Interactive sample data**. Read the opening problem statement, then
   choose **Investigate a failure**. Twenty request lanes represent one coherent
   cohort, not twenty unrelated screenshots.
2. Follow the failed retrieval to its run. Select its stage using the keyboard
   or pointer. Read the error and correlation; expand technical details only
   when useful. The ordered text list offers the waterfall's information.
3. Compare the repaired retrieval case. Identify the changed stage and added
   downstream work. Inspect timeout and cancellation separately; those failures
   are not repaired by the retrieval change.
4. Inspect cohort costs. Usage and prices are synthetic/illustrative. Open
   recorded playback, pause/step through fixed event order, then Reset demo.
   Reduced motion starts with manual stepping.
5. Open the actual-workflow guide and local evidence documents. The preview
   requires no backend/provider calls or network fonts.

## Run the real application

Follow [the clean setup](portfolio-connected.md) with a disposable database,
loopback API on 8300, frontend on 3404 and explicitly enabled bundled launcher.

1. Select Connected and Incident. **Run bundled workload** is the explicit
   execution action; inspecting a scenario never submits work automatically.
2. Observe durable progress. Expected application failures are distinct from
   infrastructure failure and incomplete telemetry. Inspect delivery counters.
3. Open the saved cohort, failed request and actual stored spans. Check that
   request IDs, correlation, stage error, history and cost totals agree.
4. Launch Repaired and compare the same stable case. Inspect actual live collector
   events, reconnect/resume and recorded playback. Playback causes no effects.
5. Reload a saved run URL. Restart the collector using the same disposable DB
   and inspect retained results. An unfinished launch becomes interrupted and
   requires a new explicit launch; it never runs again automatically.
6. Stop only your collector to inspect the connection error. Retry after restart
   or explicitly enter sample mode. No successful fixture appears silently.

Equivalent terminal execution:

```bash
python -m agenttrace.portfolio --scenario incident --endpoint http://127.0.0.1:8300 --output artifacts/incident.json
python -m agenttrace.portfolio --scenario repaired --endpoint http://127.0.0.1:8300 --output artifacts/repaired.json
python scripts/verify_connected_portfolio.py
python scripts/benchmark_portfolio_tracing.py --collector-rate-limit 100000
python scripts/verify_connected_evidence.py
```

The benchmark flag records the dedicated collector's **actual configured** rate
limit; it does not change the running server. Use `RATE_LIMIT_REQUESTS=100000`
before starting that isolated collector. Keep the normal default for ordinary
development. See [verification](portfolio-verification.md) for commands, observed
results, screenshot paths, release candidate boundaries and unverified surfaces.

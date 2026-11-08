# Portfolio images

Three 1000×750 cards for AgentTrace, all from captures already recorded in the repository.

| File | What it shows | Source |
|---|---|---|
| `trace-01-cover.png` | `request-18` stopped at `retrieve` — error, 18.0 ms, first attempt | `docs/screenshots/sample-failure-1440.png` |
| `trace-02-connected.png` | A real connected-collector run resolved to one failed span | `docs/screenshots/connected-detail-1440.png` |
| `trace-03-runset.png` | Twenty overlapping requests: 17 completed, one failure, a timeout, a cancellation | `docs/screenshots/sample-overview-1440.png` |

**What the cards claim, and what they do not.** The point is resolution, not decoration: a failed
request becomes one named span with its error, its duration and the correlation id that follows it
through the request. The run-set card exists because that is the condition tracing is for — serial
logs do not survive twenty concurrent requests.

**Provenance.** The sample scenario is fixed telemetry with a synthetic provider, synthetic tokens and
synthetic prices; the dashboard labels it in a banner and the card repeats the limit. The second card
comes from the connected local collector: concurrency, export and persistence are real, while provider
responses and prices remain bundled fixtures. Crops are cut at whitespace, laid out 1000×750 and
downscaled with Lanczos.

**Social preview:** `docs/media/social-preview.png` is the 1280×640 GitHub card (a composite of the cover card with the repository name and thesis). Upload it in Settings → Social preview; a repo edit cannot set it.

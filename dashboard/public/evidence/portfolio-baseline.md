# Project04 baseline —2026-10-23

Inspected base `c721c3f07cb5f61b358dfe25fbc77d2e147aec92`; clean clone before
creating `feat/agenttrace-portfolio`. Historical CI counts are not reused as fresh
results. An exact Git archive of this base permitted original packaging/evidence
checks independently of concurrent task-scoped source edits.

Host: Windows, Python3.12.14 virtual environments; systemPython3.14.7 is unchanged.
Node24.21.0. CI's Python3.11/Node20 environment was not executed locally. SDK-only
environment has no FastAPI; the separate integrated environment contains the
SDK and declared server/dev extras. No provider credentials are needed.

## Observed original gates

| Command / context | Result |
| --- | --- |
| SDK: `python -m pytest -q --cov=agenttrace --cov-report=term` |132passed,75%coverage |
| Server: `python -m pytest -q --cov=app --cov-report=term` (new regression files excluded) |98passed,68%coverage |
| `python -m ruff check server/app sdk/agenttrace examples server/tests sdk/tests` |Pass on exact base archive |
| Same paths, `ruff format --check` |Pass on exact base archive |
| `python -m pyright server/app sdk/agenttrace` |0errors on exact base archive |
| `python scripts/portfolio_demo.py` then `python scripts/verify_portfolio_evidence.py` |Pass, unchanged original golden |
| `python scripts/check_forbidden_dependencies.py` |Pass |
| `python -m build sdk`, `python -m build server`, `python scripts/check_wheel_contents.py` |Both source/wheel builds and content checks pass |
| Dashboard `npm ci` |506packages installed after scoped retry |
| Dashboard unit suite |29passed across6files |
| Dashboard lint and unchanged production build |Pass after complete dependency extraction |

The append-only execution logs retain exact commands, exits and outputs. Test
directories use dedicated `--basetemp` paths. Initial sandbox runs encountered
Windows temporary-directory ACL errors; scoped elevated reruns provided the
reported valid results. An initial build launched before npm finished extracting
types failed; the unchanged post-install build passed. Neither environmental
failure is described as an application regression.

## Behavior preserved before repairs

- Two overlapping requests sharing one tracer: one succeeds and the other raises
  `A run is already in progress`. The new SDK regression also exposed child/
  thread stack interference, enclosing-context loss, cancellation and late spans.
- Eight collector regressions failed against original behavior: duplicate
  ingestion, terminal-run overwrite, credential persistence, missing cohort
  filters, repeated-stage comparison, start-time live cursor and missing bounded
  launch endpoints. Expected status assertions expose behavior, not import errors.
- A connected network failure resolved to successful sample data. A focused
  frontend regression expected rejection and failed against that behavior.
- Metadata capture tests separately exposed raw prompt/message copies in wrapper
  metadata; input/output redaction alone was insufficient.

## Dependency findings and source authority

The initial lockfile audit reported12findings:2moderate,9high,1critical. This is
an inventory, not evidence that a particular exploit was reachable in the app.
The implementation updates affected runtime/test packages before final gates.

Checked official maintainer advisories2026-10-23:

- [Next typed-array cache RCE](https://github.com/vercel/next.js/security/advisories/GHSA-673q-mjm6-r5xr), patched16.4.1.
- [Next SVG image optimization RCE](https://github.com/vercel/next.js/security/advisories/GHSA-2464-fhr4-w9xw), patched16.4.1; upstream sharp fix0.35.5.
- [Vitest Windows mock redirect traversal](https://github.com/vitest-dev/vitest/security/advisories/GHSA-xp26-3454-mjgp), patched4.1.12.

See [final verification](portfolio-verification.md) for current results and
remaining findings. The pinned [GenAI conventions](GENAI_CONVENTIONS.md) are a
separate source-bound interoperability contract. Native providers, hosted CI,
human validation and deployment claims remain unverified.

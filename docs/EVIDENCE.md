# Reproducible portfolio evidence

Run `make evidence` from the repository root. The command executes a fixed
SQLite/in-memory scenario with no credentials or network access and writes an
ignored bundle to `artifacts/portfolio/agenttrace-evidence/`.

The bundle contains:

- `manifest.json` — schema, mode, result hash, reproducibility hash, and
  redaction statement;
- `report.json` — canonical, sorted JSON for the trace, cost, OTLP metadata,
  sampling decision, realtime event, redacted audit record, and issue-to-draft-PR
  safety scenario;
- `report.md` — a short human-readable explanation of the scenario;
- `checksums.sha256` — SHA-256 checksums for every generated file.

The issue/PR section uses the real dependency-free SDK package to cover issue
intake, deterministic planning, traversal and protected-branch refusal, a safe
edit, failing- then passing-test decisions, approval pause, draft-only intent,
ordered audit/trace events, replay, and redaction. It uses deterministic in-memory
providers and reports zero network calls.

`scripts/verify_portfolio_evidence.py` fails clearly for missing, extra, malformed,
tampered, or checksum-invalid files, result/reproducibility mismatches, or drift
from `server/tests/fixtures/golden/portfolio-evidence.json`. The normalized fixture
excludes timestamps, durations, generated run IDs, local paths, credentials,
environment values, and provider receipts. Generated evidence is not committed;
the small golden fixture is.

The current Python verification result is 132 SDK tests and 98 server tests. The
unchanged dashboard retains its previously verified 24-test baseline pending the
portfolio-wide clean frontend rerun.

For a portfolio walkthrough, show the command, open `report.md`, inspect the
canonical JSON, tamper with a copy to demonstrate a failed checksum, and then
re-run verification. This is evidence of engineering judgment, not a claim of
hosted production availability.

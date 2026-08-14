# Reproducible portfolio evidence

Run `make evidence` from the repository root. The command executes a fixed
SQLite/in-memory scenario with no credentials or network access and writes an
ignored bundle to `artifacts/portfolio/agenttrace-evidence/`.

The bundle contains:

- `manifest.json` — schema, mode, result hash, reproducibility hash, and
  redaction statement;
- `report.json` — canonical, sorted JSON for the trace, cost, OTLP metadata,
  sampling decision, realtime event, and redacted audit record;
- `report.md` — a short human-readable explanation of the scenario;
- `checksums.sha256` — SHA-256 checksums for every generated file.

`scripts/verify_portfolio_evidence.py` fails clearly for missing files,
malformed manifests, checksum mismatches, result/reproducibility mismatches,
or drift from `server/tests/fixtures/golden/portfolio-evidence.json`. The
normalized fixture intentionally excludes timestamps, runtime durations,
generated IDs, and local paths. Generated evidence is not committed; the small
golden fixture is.

For a portfolio walkthrough, show the command, open `report.md`, inspect the
canonical JSON, tamper with a copy to demonstrate a failed checksum, and then
re-run verification. This is evidence of engineering judgment, not a claim of
hosted production availability.

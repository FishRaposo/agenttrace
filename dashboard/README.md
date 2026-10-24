# AgentTrace investigation dashboard

This dashboard offers two explicit data sources. **Connected collector** reads actual saved runs and launches the same packaged workload as the Python CLI. **Interactive sample data** is a fixed, credential-free investigation with no backend/provider/external-font requests. A transport failure remains an error; it never changes the source.

The sample and actual workload both cover twenty overlapping requests. Incident has seventeen completed requests, a retrieval failure, a provider timeout and a cancellation. Repaired changes retrieval only: eighteen complete, while timeout and cancellation remain. Provider responses, token counts and prices are synthetic. Request timing, delivery and persistence are real only in connected execution.

## Local production workflow

Use the collector configuration in [the connected setup](../docs/portfolio-connected.md), with loopback binding, a disposable SQLite database, explicit browser origin and `PORTFOLIO_LAUNCH_ENABLED=true`. The optional SDK must be installed in the collector environment to enable launching.

PowerShell, from this directory:

```powershell
npm ci
$env:NEXT_PUBLIC_API_URL = 'http://127.0.0.1:8300'
$env:NEXT_PUBLIC_DEMO_MODE = '0'
npm run build
npm run start -- --hostname 127.0.0.1 --port 3404
```

Build and browser execution must be sequential. The production build supports new run UUIDs and direct reloads. The data-source/cohort preference is stored in versioned local storage. Sample scenario, tour and playback state reset on reload; **Reset demo** restores incident and closes the tour together. The connected launcher restores its last execution status within the tab, without silently relaunching it or replacing a manually selected cohort with a completed historical job.

In connected mode, select a workload scenario and explicitly click **Run bundled workload**. Its result separates application outcomes from delivery completeness. Use the selected cohort consistently in Overview, Runs, Costs and Live. Deep-linked runs expose their own immutable identity and can select their originating cohort. Comparisons align logical stages and show unknown/incompatible revision evidence explicitly. Playback reads recorded steps and never executes tools.

## Verification

```powershell
npm test -- --pool=threads --maxWorkers=1
npm run lint
npm run build
$env:PLAYWRIGHT_EXECUTABLE_PATH = 'C:/path/to/chrome.exe' # only if the Playwright-managed browser is unavailable
npm run test:e2e -- --project=chromium
```

The offline suite starts the production dashboard on3404, explicitly selects sample data and verifies all three required layouts (390×844, 768×1024, 1440×900), guided/free investigation, comparison, playback/reset, reduced motion, keyboard focus, console health and zero off-origin requests. It does not depend on a failed API call. The same run includes eight axe-core WCAG 2.1 A/AA scans across the five main routes, a run-detail route and two mobile widths; two `label-content-name-mismatch` defects found this way were repaired and are regression-covered by these scans.

The separate connected suite requires dedicated running API and production frontend processes:

```powershell
$env:PLAYWRIGHT_EXTERNAL_SERVER = '1'
$env:AGENTTRACE_API_URL = 'http://127.0.0.1:8300'
$env:AGENTTRACE_LEGACY_RUN_ID = 'the-verified-legacy-run-uuid'
npm run test:e2e:live -- --project=chromium
```

It performs real launches and reads stored reports through actual API responses. No successful API responses are mocked. The explicit outage phase aborts only the configured collector transport, verifies an error and retries after restoring access. SQLite restart/migration and fault injection are additionally verified by the collector integration harness; see the project verification record for actual observed results and limitations.

`/workflow` links the packaged `public/evidence` Markdown documents generated from the verified project documentation. Those files are copies for local inspection, not public publication or hosted CI evidence.

As of the 2026-10-24 audit, `npm audit` reports zero findings (the remaining dev-ESLint `zod` advisory was cleared by an in-range upgrade). See the dated verification record for dependency details. This local dashboard does not claim hosted multi-user authentication, provider trials or production-scale performance.

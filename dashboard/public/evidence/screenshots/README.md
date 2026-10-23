# Rendered AgentTrace evidence — 2026-10-23

These are screenshots of the actual production dashboard, captured with Chromium.
They were inspected for meaningful rendering, readable failures/comparisons and
responsive layout. They are separate from the assertions and stored JSON in
[verification](../portfolio-verification.md). Sample data is explicitly labeled;
connected images show the actual locally executed synthetic workload.

| Experience | 390×844 | 768×1024 | 1440×900 |
| --- | --- | --- | --- |
| Sample request cohort | [Mobile](sample-overview-390.png) | [Tablet](sample-overview-768.png) | [Desktop](sample-overview-1440.png) |
| Sample retrieval failure | [Mobile](sample-failure-390.png) | [Tablet](sample-failure-768.png) | [Desktop](sample-failure-1440.png) |
| Sample repaired comparison | [Mobile](sample-comparison-390.png) | [Tablet](sample-comparison-768.png) | [Desktop](sample-comparison-1440.png) |
| Connected recorded request | [Mobile](connected-detail-390.png) | [Tablet](connected-detail-768.png) | [Desktop](connected-detail-1440.png) |

[Connected repaired comparison](connected-comparison.png) shows actual persisted
records aligned by stage. Provider answers, usage and prices remain synthetic;
request concurrency, SDK export and SQLite persistence are real. Full-page images
may be taller than the viewport; no screenshot manipulation was used.

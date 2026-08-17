# Third-party notices

## Internally vendored operator core subset

The server contains a narrow, internally namespaced copy of the modules needed
for configuration, database access, errors, logging, rate limiting, LLM metrics,
pricing, Redis helpers, HTTP clients, and tracing. The source is pinned to
`FishRaposo/operator-shared-core` commit
`dbf276a7708da65b55e1f10b35af634b300d1f07` (2026-08-14).

The copied modules remain under the original MIT License:

Copyright (c) 2026 Vinícius Raposo

No external `shared_core` package is installed or imported at runtime. The SDK
does not use these modules and remains independently installable.

## github-issue-pr-agent capability lineage

The dependency-free `agenttrace.issue_pr` package adapts selected safety and
workflow concepts from `FishRaposo/github-issue-pr-agent` commit
`01a2404ecf2f6f2cea5ea873c37b63ed1b1dde20`, originally published under the MIT
License (Copyright (c) 2026 Operator Systems). The dated absorption decision
maps each source module to its AgentTrace-owned replacement. The source
project's server, persistence layer, external `shared_core` dependency, and
hosted provider integrations were not copied.

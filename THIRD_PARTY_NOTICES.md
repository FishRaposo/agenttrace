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

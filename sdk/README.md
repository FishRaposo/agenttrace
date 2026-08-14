# AgentTrace SDK

Standalone, dependency-light tracing SDK for agentic workflows. Install the
server separately when HTTP collection, replay, or the dashboard is needed:

```bash
pip install -e "sdk[dev]"
```

The SDK records runs and spans locally and can export JSONL or HTTP payloads;
it never imports the FastAPI server or its vendored compatibility layer.

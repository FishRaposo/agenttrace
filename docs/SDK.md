# SDK Guide

## Installation

```bash
pip install agenttrace
```

For local development:

```bash
cd sdk
pip install -e .
```

## Quickstart

```python
from agenttrace import Tracer
from agenttrace.exporters import JSONLExporter

tracer = Tracer()
tracer.set_exporter(JSONLExporter("traces.jsonl"))

run = tracer.start_run("my_agent_run")
span = tracer.start_span("greeting_call", "llm_call")
span.end(output="Hello, world!")
tracer.end_run(status="completed")
tracer.flush()
```

## Decorator Usage

### Trace LLM Calls

```python
from agenttrace import Tracer
from agenttrace.wrappers import trace_llm

tracer = Tracer()

@trace_llm(tracer)
def call_gpt(prompt: str, model: str = "gpt-4") -> str:
    response = openai.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

result = call_gpt("Explain quantum computing")
```

### Trace Tool Calls

```python
from agenttrace.wrappers import trace_tool

@trace_tool(tracer)
def search_web(query: str) -> list[dict]:
    return web_search_api(query)

results = search_web("quantum computing")
```

## Context Manager Usage

```python
from agenttrace import Tracer

tracer = Tracer()

with tracer.run("context_example") as run:
    with tracer.span("step_1", "llm_call") as span:
        result = call_llm("Hello")
        span.set_output(result)

    with tracer.span("step_2", "tool_call") as span:
        data = fetch_data()
        span.set_output(data)
```

## Configuration

```python
from agenttrace import Tracer
from agenttrace.exporters import APIExporter, JSONLExporter

tracer = Tracer()

# Use JSONL for local development
tracer.set_exporter(JSONLExporter("dev_traces.jsonl"))

# Use API exporter for production
tracer.set_exporter(APIExporter(
    endpoint="http://localhost:8000/api",
    buffer_size=50,
    max_retries=3,
))
```

## Safety-bounded issue-to-draft-PR workflow

`agenttrace.issue_pr` is an additive, dependency-free SDK package absorbed from
the former `github-issue-pr-agent` project. It provides provider-neutral issue and
planning protocols, exact sandbox edits, protected-branch guards, shell-free
bounded test execution, explicit approval state, a draft-only sink protocol,
ordered redacted audit events, AgentTrace event forwarding, and deterministic
run/audit replay.

The included `StaticIssueSource`, `DeterministicPlanProvider`, and
`RecordingDraftPullRequestSink` are offline adapters. `IssuePRWorkflow.process()`
stops at `awaiting_approval`; `approve()` is the only path to the draft sink.
The SDK never merges, refuses `main`/`master` mutations, and does not import or
contact GitHub by default.

GitHub REST, LLM planning, PostgreSQL, Redis, Celery, GitPython, and PyGithub
adapters are intentionally outside the default package path.

## Exporter Options

### JSONLExporter
- **path**: Output file path
- **buffer_size**: Number of entries to buffer before writing

### APIExporter
- **endpoint**: Trace server API base URL (`/api`) or trace endpoint (`/api/traces`)
- **buffer_size**: Number of entries to buffer before sending
- **max_retries**: Maximum retry attempts
- **timeout**: Request timeout in seconds

## Best Practices

- Always call `tracer.flush()` before your program exits
- Use descriptive `name` values for runs and spans
- Include relevant `metadata` for filtering and debugging
- Handle exporter errors gracefully — the agent should never crash due to tracing

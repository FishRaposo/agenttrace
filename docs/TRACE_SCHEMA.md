# Trace Schema

## Run

Represents a complete agent execution from start to finish.

| Field | Type | Description |
|---|---|---|
| `id` | `UUID` | Unique run identifier |
| `name` | `str` | Human-readable run name |
| `status` | `RunStatus` | `running`, `completed`, `failed`, `cancelled` |
| `start_time` | `datetime` | ISO 8601 timestamp when run started |
| `end_time` | `datetime \| null` | ISO 8601 timestamp when run ended |
| `total_cost` | `float` | Aggregate cost in USD |
| `total_tokens` | `int` | Aggregate token count |
| `span_count` | `int` | Number of spans in this run |
| `metadata` | `dict \| null` | Arbitrary run-level metadata |

### Run JSON Example

```json
{
  "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "name": "research_task",
  "status": "completed",
  "start_time": "2025-01-15T10:30:00Z",
  "end_time": "2025-01-15T10:30:45Z",
  "total_cost": 0.0087,
  "total_tokens": 4250,
  "span_count": 5,
  "metadata": {
    "query": "quantum computing basics",
    "agent_version": "1.0.0"
  }
}
```

## Span

Represents a single operation within a run.

| Field | Type | Description |
|---|---|---|
| `id` | `UUID` | Unique span identifier |
| `run_id` | `UUID` | Parent run identifier |
| `parent_span_id` | `UUID \| null` | Parent span for nesting |
| `name` | `str` | Span name (e.g. "gpt-4 call", "web_search") |
| `span_type` | `SpanType` | `llm_call`, `tool_call`, `decision`, `retrieval`, `custom` |
| `status` | `SpanStatus` | `started`, `completed`, `error` |
| `input_data` | `any` | Input payload (prompt, arguments) |
| `output_data` | `any` | Output payload (completion, result) |
| `metadata` | `dict \| null` | Span-specific metadata |
| `start_time` | `datetime` | When span started |
| `end_time` | `datetime \| null` | When span ended |
| `duration_ms` | `float \| null` | Duration in milliseconds |
| `cost_usd` | `float \| null` | Cost in USD (LLM spans) |
| `token_usage` | `TokenUsage \| null` | Token counts (LLM spans) |
| `error` | `str \| null` | Error message if failed |

### Span JSON Example

```json
{
  "id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
  "run_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "parent_span_id": null,
  "name": "gpt-4 synthesis",
  "span_type": "llm_call",
  "status": "completed",
  "input_data": "Summarize the following search results...",
  "output_data": "Quantum computing leverages quantum mechanics...",
  "metadata": {
    "model": "gpt-4",
    "temperature": 0.7
  },
  "start_time": "2025-01-15T10:30:10Z",
  "end_time": "2025-01-15T10:30:15Z",
  "duration_ms": 5200,
  "cost_usd": 0.0045,
  "token_usage": {
    "prompt_tokens": 1200,
    "completion_tokens": 800,
    "total_tokens": 2000
  },
  "error": null
}
```

## SpanType Enum

| Value | Description |
|---|---|
| `llm_call` | Large language model API call |
| `tool_call` | External tool or function invocation |
| `decision` | Agent decision or branching point |
| `retrieval` | Document or knowledge retrieval |
| `custom` | User-defined span type |

## RunStatus Enum

| Value | Description |
|---|---|
| `running` | Run is currently executing |
| `completed` | Run finished successfully |
| `failed` | Run encountered an error |
| `cancelled` | Run was manually cancelled |

## TokenUsage

| Field | Type | Description |
|---|---|---|
| `prompt_tokens` | `int` | Tokens in the prompt |
| `completion_tokens` | `int` | Tokens in the completion |
| `total_tokens` | `int` | Sum of prompt + completion |

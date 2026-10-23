# GenAI JSON interoperability subset

Frozen2026-10-23 before mapping changes. Official source: OpenTelemetry
semantic-conventions-genai commit
[`9ffc7e00c639be7712e544e3e54331e885dccf84`](https://github.com/open-telemetry/semantic-conventions-genai/tree/9ffc7e00c639be7712e544e3e54331e885dccf84).

The selected attributes remain **development conventions**, not a stable universal
compatibility promise. This release candidate supports OTLP HTTP JSON against
the actual AgentTrace collector. Protobuf, gRPC and other collectors are outside
this verification.

| Attribute | Meaning |
| --- | --- |
| `gen_ai.operation.name` | Operation such as chat or embeddings |
| `gen_ai.provider.name` | Provider identified by the instrumentation |
| `gen_ai.request.model` | Requested model |
| `gen_ai.response.model` | Returned model, when known |
| `gen_ai.usage.input_tokens` | Recorded input usage |
| `gen_ai.usage.output_tokens` | Recorded output usage |

Preserve legacy AgentTrace/LLM aliases. Unknown information remains absent rather
than fabricated. Bundled workload provider and usage values are synthetic;
illustrative pricing is separate from observed provider billing. Cancellation is
an AgentTrace outcome, with its original status retained in attributes when OTLP
cannot represent it directly.

Source files retrieved from that commit:

- [Span conventions](https://github.com/open-telemetry/semantic-conventions-genai/blob/9ffc7e00c639be7712e544e3e54331e885dccf84/docs/gen-ai/gen-ai-spans.md)
- [Attribute registry](https://github.com/open-telemetry/semantic-conventions-genai/blob/9ffc7e00c639be7712e544e3e54331e885dccf84/docs/registry/attributes/gen-ai.md)

Retrieved-file SHA-256 values (UTF-8 response bytes):

| File | SHA-256 |
| --- | --- |
| `docs/gen-ai/gen-ai-spans.md` | `df6f7bb1911dfe35d286c84971d8227a8f0e765cb3ad3be1532441371c17b69e` |
| `docs/registry/attributes/gen-ai.md` | `cb2fff3d70a08e2f5f180dae7514f973b81b2855d6ce3511cd06997b30fd9974` |

The execution ledger stores the retrieved files. The connected verification
report records the SDK exporter → collector round trip.

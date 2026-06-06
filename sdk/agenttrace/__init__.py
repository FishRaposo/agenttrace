"""AgentTrace SDK — observability and replay layer for agentic AI workflows."""

from agenttrace.cost_tracker import CostTracker
from agenttrace.tracer import Tracer
from agenttrace.span import Span, SpanType, SpanStatus
from agenttrace.wrappers.provider_wrappers import trace_openai, trace_anthropic
from agenttrace.hybrid_client import HybridLLMClient, HybridResponse
from agenttrace.instrumentation import auto_instrument

__version__ = "0.1.0"
__all__ = [
    "Tracer",
    "Span",
    "SpanType",
    "SpanStatus",
    "CostTracker",
    "trace_openai",
    "trace_anthropic",
    "HybridLLMClient",
    "HybridResponse",
    "auto_instrument",
]

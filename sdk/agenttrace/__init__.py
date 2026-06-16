"""AgentTrace SDK — observability and replay layer for agentic AI workflows."""

from agenttrace.cost_tracker import CostTracker
from agenttrace.hybrid_client import HybridLLMClient, HybridResponse
from agenttrace.instrumentation import auto_instrument
from agenttrace.span import Span, SpanStatus, SpanType
from agenttrace.tracer import Tracer
from agenttrace.wrappers.provider_wrappers import trace_anthropic, trace_openai

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

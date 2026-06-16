"""Wrappers package — automatic instrumentation decorators."""

from agenttrace.wrappers.decision_wrapper import trace_decision
from agenttrace.wrappers.llm_wrapper import trace_llm
from agenttrace.wrappers.provider_wrappers import trace_anthropic, trace_openai
from agenttrace.wrappers.retrieval_wrapper import trace_retrieval
from agenttrace.wrappers.tool_wrapper import trace_tool

__all__ = [
    "trace_llm",
    "trace_openai",
    "trace_anthropic",
    "trace_tool",
    "trace_decision",
    "trace_retrieval",
]

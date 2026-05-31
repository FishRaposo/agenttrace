"""Wrappers package — automatic instrumentation decorators."""

from agenttrace.wrappers.llm_wrapper import trace_llm
from agenttrace.wrappers.tool_wrapper import trace_tool
from agenttrace.wrappers.decision_wrapper import trace_decision
from agenttrace.wrappers.retrieval_wrapper import trace_retrieval

__all__ = ["trace_llm", "trace_tool", "trace_decision", "trace_retrieval"]

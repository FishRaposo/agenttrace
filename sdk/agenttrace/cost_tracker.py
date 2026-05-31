"""Cost tracking integration for AgentTrace.

Tracks LLM costs per trace, workflow, and feature.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class CostRecord:
    """Cost record for a trace."""
    trace_id: str
    provider: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    cost_usd: float
    latency_ms: int
    workflow_id: str | None = None
    feature: str | None = None


class CostTracker:
    """Track costs for AgentTrace spans.
    
    Features:
    - Per-trace cost attribution
    - Per-workflow cost aggregation
    - Model cost comparison
    - Budget threshold alerts
    """
    
    # Provider pricing per 1K tokens
    PRICING = {
        "openai": {
            "gpt-4": {"prompt": 0.03, "completion": 0.06},
            "gpt-4-turbo": {"prompt": 0.01, "completion": 0.03},
            "gpt-3.5-turbo": {"prompt": 0.0015, "completion": 0.002},
        },
        "anthropic": {
            "claude-3-opus": {"prompt": 0.015, "completion": 0.075},
            "claude-3-sonnet": {"prompt": 0.003, "completion": 0.015},
            "claude-3-haiku": {"prompt": 0.00025, "completion": 0.00125},
        },
    }
    
    def __init__(self) -> None:
        """Initialize cost tracker."""
        self.records: list[CostRecord] = []
    
    def get_pricing(self, provider: str, model: str) -> dict[str, float] | None:
        """Get pricing for a provider/model.

        Returns:
            Dict with 'prompt' and 'completion' per-1k-token rates, or None.
        """
        provider_pricing = self.PRICING.get(provider, {})
        return provider_pricing.get(model)

    def calculate_cost(
        self,
        provider: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> float:
        """Calculate cost for a request."""
        provider_pricing = self.PRICING.get(provider, {})
        model_pricing = provider_pricing.get(model, {"prompt": 0.0, "completion": 0.0})
        
        prompt_cost = (prompt_tokens / 1000) * model_pricing["prompt"]
        completion_cost = (completion_tokens / 1000) * model_pricing["completion"]
        
        return round(prompt_cost + completion_cost, 6)
    
    def record_cost(
        self,
        trace_id: str,
        provider: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        latency_ms: int,
        workflow_id: str | None = None,
        feature: str | None = None,
    ) -> CostRecord:
        """Record cost for a trace."""
        cost = self.calculate_cost(provider, model, prompt_tokens, completion_tokens)
        
        record = CostRecord(
            trace_id=trace_id,
            provider=provider,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost_usd=cost,
            latency_ms=latency_ms,
            workflow_id=workflow_id,
            feature=feature,
        )
        
        self.records.append(record)
        return record
    
    def get_workflow_cost(self, workflow_id: str) -> dict[str, Any]:
        """Get aggregated cost for a workflow."""
        workflow_records = [r for r in self.records if r.workflow_id == workflow_id]
        
        total_cost = sum(r.cost_usd for r in workflow_records)
        total_tokens = sum(r.prompt_tokens + r.completion_tokens for r in workflow_records)
        avg_latency = sum(r.latency_ms for r in workflow_records) / len(workflow_records) if workflow_records else 0
        
        return {
            "workflow_id": workflow_id,
            "total_cost": total_cost,
            "total_tokens": total_tokens,
            "request_count": len(workflow_records),
            "average_latency_ms": avg_latency,
        }
    
    def get_feature_cost(self, feature: str) -> dict[str, Any]:
        """Get aggregated cost for a feature."""
        feature_records = [r for r in self.records if r.feature == feature]
        
        total_cost = sum(r.cost_usd for r in feature_records)
        total_tokens = sum(r.prompt_tokens + r.completion_tokens for r in feature_records)
        
        return {
            "feature": feature,
            "total_cost": total_cost,
            "total_tokens": total_tokens,
            "request_count": len(feature_records),
        }

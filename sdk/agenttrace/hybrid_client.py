"""Hybrid LLM client — deterministic simulation or real provider calls.

Set ``AGENTTRACE_LLM_MODE=real`` to use real provider clients.
Set ``AGENTTRACE_LLM_MODE=sim`` (default) for deterministic mock responses.

Examples:
    >>> from agenttrace.hybrid_client import HybridLLMClient
    >>> client = HybridLLMClient()
    >>> response = client.chat("openai", messages=[{"role": "user", "content": "hi"}])
"""

from __future__ import annotations

import os
import random
from dataclasses import dataclass
from typing import Any

from agenttrace.tracer import Tracer
from agenttrace.wrappers.provider_wrappers import trace_anthropic, trace_openai


@dataclass
class HybridResponse:
    """Normalized response object returned by HybridLLMClient."""

    content: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    provider: str
    raw: Any | None = None


class HybridLLMClient:
    """Unified LLM client that works in simulation or real mode.

    Args:
        mode: ``"sim"`` for mock responses (default) or ``"real"`` for live API calls.
        tracer: Optional AgentTrace Tracer for automatic instrumentation.
        seed: Deterministic seed for simulated responses. Defaults to
            ``AGENTTRACE_LLM_SEED`` or 42.
    """

    def __init__(
        self,
        mode: str | None = None,
        tracer: Tracer | None = None,
        seed: int | None = None,
        provider_priority: list[str] | None = None,
    ) -> None:
        self.mode = (mode or os.getenv("AGENTTRACE_LLM_MODE", "sim")).lower()
        self.tracer = tracer
        self.seed = (
            seed if seed is not None else int(os.getenv("AGENTTRACE_LLM_SEED", "42"))
        )
        random.seed(self.seed)

        env_priority = os.getenv("AGENTTRACE_PROVIDER_PRIORITY", "")
        if env_priority:
            self.provider_priority = [p.strip() for p in env_priority.split(",")]
        elif provider_priority:
            self.provider_priority = list(provider_priority)
        else:
            self.provider_priority = ["openai", "anthropic"]

        self._openai_client: Any | None = None
        self._anthropic_client: Any | None = None

    def _get_openai(self) -> Any:
        if self._openai_client is None:
            try:
                import openai  # noqa: PLC0415
            except ImportError as exc:
                raise RuntimeError(
                    "OpenAI client not installed. Run: pip install openai"
                ) from exc
            self._openai_client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        return self._openai_client

    def _get_anthropic(self) -> Any:
        if self._anthropic_client is None:
            try:
                import anthropic  # noqa: PLC0415
            except ImportError as exc:
                raise RuntimeError(
                    "Anthropic client not installed. Run: pip install anthropic"
                ) from exc
            self._anthropic_client = anthropic.Anthropic(
                api_key=os.getenv("ANTHROPIC_API_KEY")
            )
        return self._anthropic_client

    def _simulate(self, prompt: str, model: str, provider: str) -> HybridResponse:
        """Generate a deterministic mock response."""
        # Deterministic "response" based on prompt hash
        prompt_hash = sum(ord(c) for c in prompt)
        random.seed(self.seed + prompt_hash)

        responses = [
            "Certainly! Here's what I found.",
            "Based on the context provided, the answer is positive.",
            "I would recommend the following approach.",
            "The analysis suggests a moderate confidence level.",
            "Here is a summary of the key findings.",
        ]
        content = responses[prompt_hash % len(responses)]
        completion_tokens = 20 + (prompt_hash % 80)
        prompt_tokens = 10 + (len(prompt) // 4)

        return HybridResponse(
            content=content,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            provider=provider,
            raw=None,
        )

    def chat(
        self,
        provider: str | list[str] | None = None,
        model: str = "",
        messages: list[dict[str, str]] | None = None,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> HybridResponse:
        """Send a chat completion request with optional multi-provider fallback.

        Args:
            provider: Single provider name, list to try in order, or None to
                use priority list.
            model: Model identifier.
            messages: Conversation messages.
            temperature: Sampling temperature.
            **kwargs: Additional provider-specific arguments.

        Returns:
            Normalized HybridResponse.
        """
        messages = messages or []
        prompt = messages[-1].get("content", "") if messages else ""

        providers = []
        if isinstance(provider, str):
            providers = [provider]
        elif isinstance(provider, list):
            providers = provider
        else:
            providers = self.provider_priority

        if self.mode == "sim":
            return self._simulate(prompt, model, providers[0])

        last_error: Exception | None = None
        for prov in providers:
            try:
                if prov == "openai":
                    return self._chat_openai(model, messages, temperature, **kwargs)
                if prov == "anthropic":
                    return self._chat_anthropic(model, messages, temperature, **kwargs)
                raise ValueError(f"Unknown provider: {prov}")
            except Exception as exc:
                last_error = exc
                continue

        raise last_error or RuntimeError("All providers failed")

    def _chat_openai(
        self,
        model: str,
        messages: list[dict[str, str]],
        temperature: float,
        **kwargs: Any,
    ) -> HybridResponse:
        client = self._get_openai()

        def _call() -> Any:
            return client.chat.completions.create(
                model=model,
                messages=messages,  # type: ignore[arg-type]
                temperature=temperature,
                **kwargs,
            )

        wrapped = _call
        if self.tracer is not None:
            wrapped = trace_openai(tracer=self.tracer, model=model)(_call)

        raw = wrapped()
        content = raw.choices[0].message.content if raw.choices else ""
        usage = raw.usage
        return HybridResponse(
            content=content or "",
            model=raw.model or model,
            prompt_tokens=getattr(usage, "prompt_tokens", 0),
            completion_tokens=getattr(usage, "completion_tokens", 0),
            total_tokens=getattr(usage, "total_tokens", 0),
            provider="openai",
            raw=raw,
        )

    def _chat_anthropic(
        self,
        model: str,
        messages: list[dict[str, str]],
        temperature: float,
        **kwargs: Any,
    ) -> HybridResponse:
        client = self._get_anthropic()

        def _call() -> Any:
            return client.messages.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=kwargs.get("max_tokens", 1024),
                **{k: v for k, v in kwargs.items() if k != "max_tokens"},
            )

        wrapped = _call
        if self.tracer is not None:
            wrapped = trace_anthropic(tracer=self.tracer, model=model)(_call)

        raw = wrapped()
        content = ""
        if hasattr(raw, "content") and raw.content:
            content = (
                raw.content[0].text
                if hasattr(raw.content[0], "text")
                else str(raw.content[0])
            )
        usage = raw.usage
        input_tokens = getattr(usage, "input_tokens", 0)
        output_tokens = getattr(usage, "output_tokens", 0)
        return HybridResponse(
            content=content,
            model=raw.model or model,
            prompt_tokens=input_tokens,
            completion_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            provider="anthropic",
            raw=raw,
        )

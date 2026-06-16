"""Tests for HybridLLMClient."""

from __future__ import annotations

import pytest
from agenttrace.hybrid_client import HybridLLMClient, HybridResponse


class TestHybridLLMClient:
    def test_sim_mode_default(self) -> None:
        client = HybridLLMClient(mode="sim", seed=42)
        assert client.mode == "sim"
        resp = client.chat(
            "openai", "gpt-4", messages=[{"role": "user", "content": "hello"}]
        )
        assert isinstance(resp, HybridResponse)
        assert resp.content
        assert resp.prompt_tokens > 0
        assert resp.completion_tokens > 0
        assert resp.total_tokens > 0
        assert resp.provider == "openai"

    def test_sim_mode_deterministic(self) -> None:
        """Same prompt + seed should yield same response."""
        client = HybridLLMClient(mode="sim", seed=42)
        r1 = client.chat(
            "openai", "gpt-4", messages=[{"role": "user", "content": "test"}]
        )
        r2 = client.chat(
            "openai", "gpt-4", messages=[{"role": "user", "content": "test"}]
        )
        assert r1.content == r2.content
        assert r1.prompt_tokens == r2.prompt_tokens
        assert r1.completion_tokens == r2.completion_tokens

    def test_sim_mode_anthropic(self) -> None:
        client = HybridLLMClient(mode="sim", seed=42)
        resp = client.chat(
            "anthropic", "claude-3", messages=[{"role": "user", "content": "hi"}]
        )
        assert resp.provider == "anthropic"
        assert resp.total_tokens > 0

    def test_sim_mode_accepts_any_provider(self) -> None:
        """Simulation mode accepts any provider string."""
        client = HybridLLMClient(mode="sim")
        resp = client.chat("cohere", "cmd-r", messages=[])
        assert resp.provider == "cohere"

    def test_real_mode_without_key_raises(self) -> None:
        """Real mode without env keys should raise an error."""
        client = HybridLLMClient(mode="real")
        # OpenAI client raises OpenAIError for missing key in newer versions
        with pytest.raises((RuntimeError, Exception)):
            client.chat("openai", "gpt-4", messages=[{"role": "user", "content": "hi"}])

"""Tests for the cost tracker."""

from __future__ import annotations

import json

from agenttrace.cost_tracker import CostTracker


class TestCalculateCost:
    def test_known_model(self) -> None:
        tracker = CostTracker()
        # gpt-4: prompt 0.03/1k, completion 0.06/1k
        cost = tracker.calculate_cost("openai", "gpt-4", 1000, 1000)
        assert cost == round(0.03 + 0.06, 6)

    def test_unknown_model_defaults_to_zero(self) -> None:
        tracker = CostTracker()
        assert tracker.calculate_cost("openai", "does-not-exist", 1000, 1000) == 0.0

    def test_external_pricing_entry_missing_keys(self, tmp_path, monkeypatch) -> None:
        """An external pricing entry missing prompt/completion must not raise.

        Previously model_pricing['prompt'] raised KeyError; the fix uses
        .get(..., 0.0) so a partial entry degrades gracefully.
        """
        pricing_file = tmp_path / "pricing.json"
        # Entry present but missing both 'prompt' and 'completion' keys, plus
        # one with only 'prompt' to exercise the partial path.
        pricing_file.write_text(
            json.dumps(
                {
                    "openai": {
                        "weird-model": {"notes": "no rates here"},
                        "prompt-only": {"prompt": 0.01},
                    }
                }
            )
        )
        monkeypatch.setenv("AGENTTRACE_PRICING_FILE", str(pricing_file))

        tracker = CostTracker()

        # Missing both keys -> 0.0, no KeyError.
        assert tracker.calculate_cost("openai", "weird-model", 1000, 1000) == 0.0
        # Missing only 'completion' -> just the prompt cost.
        assert tracker.calculate_cost("openai", "prompt-only", 1000, 1000) == round(
            0.01, 6
        )

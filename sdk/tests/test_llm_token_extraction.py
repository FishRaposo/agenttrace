"""Tests for enhanced token extraction from llm_wrapper."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
from agenttrace.tracer import Tracer
from agenttrace.wrappers.llm_wrapper import (
    _extract_token_usage,
    _parse_token_string,
    trace_llm,
)


class TestExtractTokenUsageDict:
    """Tests for dict-based token extraction."""

    def test_standard_openai_dict(self) -> None:
        result = {
            "choices": [{"text": "Hello"}],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 20,
                "total_tokens": 30,
            },
        }
        usage = _extract_token_usage(result)
        assert usage is not None
        assert usage["prompt_tokens"] == 10
        assert usage["completion_tokens"] == 20
        assert usage["total_tokens"] == 30

    def test_dict_with_zero_tokens(self) -> None:
        result = {
            "usage": {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
            },
        }
        usage = _extract_token_usage(result)
        assert usage is not None
        assert usage["prompt_tokens"] == 0
        assert usage["completion_tokens"] == 0

    def test_dict_without_usage_key(self) -> None:
        result = {"choices": [{"text": "ok"}]}
        usage = _extract_token_usage(result)
        assert usage is None


class TestExtractTokenUsageObject:
    """Tests for object attribute token extraction."""

    def test_object_with_usage_dict_attr(self) -> None:
        result = SimpleNamespace(
            usage={"prompt_tokens": 15, "completion_tokens": 25, "total_tokens": 40}
        )
        usage = _extract_token_usage(result)
        assert usage is not None
        assert usage["prompt_tokens"] == 15
        assert usage["completion_tokens"] == 25
        assert usage["total_tokens"] == 40

    def test_object_with_usage_attrs(self) -> None:
        result = SimpleNamespace(
            usage=SimpleNamespace(prompt_tokens=5, completion_tokens=7, total_tokens=12)
        )
        usage = _extract_token_usage(result)
        assert usage is not None
        assert usage["prompt_tokens"] == 5
        assert usage["completion_tokens"] == 7
        assert usage["total_tokens"] == 12

    def test_object_with_input_output_tokens(self) -> None:
        result = SimpleNamespace(
            usage=SimpleNamespace(input_tokens=30, output_tokens=50)
        )
        usage = _extract_token_usage(result)
        assert usage is not None
        assert usage["prompt_tokens"] == 30
        assert usage["completion_tokens"] == 50
        assert usage["total_tokens"] == 80

    def test_object_with_usage_metadata(self) -> None:
        result = SimpleNamespace(
            usage_metadata=SimpleNamespace(
                prompt_token_count=8, candidates_token_count=12
            )
        )
        usage = _extract_token_usage(result)
        assert usage is not None
        assert usage["prompt_tokens"] == 8
        assert usage["completion_tokens"] == 12
        assert usage["total_tokens"] == 20

    def test_object_without_usage_attr(self) -> None:
        result = SimpleNamespace(choices=[], model="gpt-4")
        usage = _extract_token_usage(result)
        assert usage is None

    def test_object_usage_with_string_values(self) -> None:
        result = SimpleNamespace(
            usage=SimpleNamespace(prompt_tokens=10, model_name="gpt-4")
        )
        usage = _extract_token_usage(result)
        assert usage is not None
        assert usage["prompt_tokens"] == 10
        assert usage["completion_tokens"] == 0


class TestExtractTokenUsageString:
    """Tests for string heuristic token extraction."""

    def test_parse_standard_token_string(self) -> None:
        text = "prompt_tokens: 10, completion_tokens: 20, total_tokens: 30"
        usage = _parse_token_string(text)
        assert usage is not None
        assert usage["prompt_tokens"] == 10
        assert usage["completion_tokens"] == 20
        assert usage["total_tokens"] == 30

    def test_parse_input_output_tokens(self) -> None:
        text = "input_tokens=15, output_tokens=25"
        usage = _parse_token_string(text)
        assert usage is not None
        assert usage["input_tokens"] == 15
        assert usage["output_tokens"] == 25

    def test_parse_partial_token_string(self) -> None:
        text = "Total prompt_tokens 55 used"
        usage = _parse_token_string(text)
        assert usage is not None
        assert usage["prompt_tokens"] == 55

    def test_parse_no_tokens_found(self) -> None:
        text = "This is a plain response with no token info"
        usage = _parse_token_string(text)
        assert usage is None

    def test_string_result_extraction(self) -> None:
        result = "prompt_tokens: 100, completion_tokens: 200, total_tokens: 300"
        usage = _extract_token_usage(result)
        assert usage is not None
        assert usage["prompt_tokens"] == 100
        assert usage["completion_tokens"] == 200
        assert usage["total_tokens"] == 300

    def test_string_without_token_patterns(self) -> None:
        result = "Just a regular response string"
        usage = _extract_token_usage(result)
        assert usage is None


class TestTraceLLMIntegration:
    """Integration tests for trace_llm with different result formats."""

    def test_dict_result_with_usage(self, tracer: Tracer) -> None:
        @trace_llm(
            tracer,
            model="gpt-4",
            cost_per_prompt_token=0.00003,
            cost_per_completion_token=0.00006,
        )
        def call_llm(prompt: str) -> dict[str, Any]:
            return {
                "choices": [{"text": "response"}],
                "usage": {
                    "prompt_tokens": 100,
                    "completion_tokens": 50,
                    "total_tokens": 150,
                },
            }

        with tracer.run("test_run"):
            result = call_llm("hello")

        assert result["choices"][0]["text"] == "response"

    def test_object_result_with_usage(self, tracer: Tracer) -> None:
        @trace_llm(
            tracer,
            model="gpt-4",
            cost_per_prompt_token=0.00003,
            cost_per_completion_token=0.00006,
        )
        def call_llm(prompt: str) -> Any:
            return SimpleNamespace(
                choices=[SimpleNamespace(text="response")],
                usage=SimpleNamespace(
                    prompt_tokens=100, completion_tokens=50, total_tokens=150
                ),
            )

        with tracer.run("test_run"):
            result = call_llm("hello")

        assert result.choices[0].text == "response"

    def test_string_result(self, tracer: Tracer) -> None:
        @trace_llm(tracer, model="gpt-4")
        def call_llm(prompt: str) -> str:
            return "Generated text response here"

        with tracer.run("test_run"):
            result = call_llm("hello")

        assert result == "Generated text response here"

    def test_exception_handling(self, tracer: Tracer) -> None:
        @trace_llm(tracer, model="gpt-4")
        def broken_llm(prompt: str) -> str:
            raise ValueError("API error")

        with pytest.raises(ValueError, match="API error"):
            with tracer.run("test_run"):
                broken_llm("hello")

    def test_cost_calculation(self, tracer: Tracer) -> None:
        @trace_llm(
            tracer,
            model="gpt-4",
            cost_per_prompt_token=0.00003,
            cost_per_completion_token=0.00006,
        )
        def call_llm(prompt: str) -> dict[str, Any]:
            return {
                "choices": [{"text": "response"}],
                "usage": {
                    "prompt_tokens": 100,
                    "completion_tokens": 50,
                    "total_tokens": 150,
                },
            }

        with tracer.run("test_run"):
            call_llm("hello")

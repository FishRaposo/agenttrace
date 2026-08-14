"""Deterministic head and tail sampling decisions."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Generic, TypeVar


@dataclass(frozen=True)
class SamplingDecision:
    """A reproducible sampling result and its reason."""

    sampled: bool
    reason: str
    score: float


T = TypeVar("T")


class SamplingPolicy:
    """Select traces using a stable SHA-256-derived score."""

    def __init__(
        self,
        *,
        mode: str = "off",
        rate: float = 1.0,
        keep_errors: bool = True,
        slow_threshold_ms: float | None = None,
    ) -> None:
        if mode not in {"off", "head", "tail"}:
            raise ValueError("sampling mode must be off, head, or tail")
        if not 0.0 <= rate <= 1.0:
            raise ValueError("sampling rate must be between 0 and 1")
        if slow_threshold_ms is not None and slow_threshold_ms < 0:
            raise ValueError("slow threshold must be non-negative")
        self.mode = mode
        self.rate = rate
        self.keep_errors = keep_errors
        self.slow_threshold_ms = slow_threshold_ms

    @staticmethod
    def _score(trace_id: str) -> float:
        digest = hashlib.sha256(trace_id.encode("utf-8")).digest()
        return int.from_bytes(digest[:8], "big") / float(2**64)

    def decide(
        self,
        *,
        trace_id: str,
        status: str | None = None,
        duration_ms: float | None = None,
        terminal: bool = True,
    ) -> SamplingDecision:
        score = self._score(trace_id)
        if self.mode == "off":
            return SamplingDecision(True, "disabled", score)

        if self.mode == "tail" and not terminal:
            return SamplingDecision(True, "tail_buffer", score)

        if self.mode == "tail" and self.keep_errors and status in {"error", "failed"}:
            return SamplingDecision(True, "tail_error", score)
        if (
            self.mode == "tail"
            and self.slow_threshold_ms is not None
            and duration_ms is not None
            and duration_ms >= self.slow_threshold_ms
        ):
            return SamplingDecision(True, "tail_slow", score)

        reason = f"{self.mode}_rate"
        return SamplingDecision(score < self.rate, reason, score)


class TailSamplingBuffer(Generic[T]):
    """Buffer spans until a run reaches a terminal sampling decision.

    The buffer is deliberately storage-agnostic.  A caller can keep the
    returned items in its transaction and persist them together, or discard
    them when the terminal decision is negative.  This keeps the SDK and the
    default in-memory server path independent of Redis or a hosted queue.
    """

    _TERMINAL_STATUSES = frozenset({"completed", "complete", "error", "failed"})

    def __init__(self, policy: SamplingPolicy) -> None:
        if policy.mode != "tail":
            raise ValueError("TailSamplingBuffer requires a tail sampling policy")
        self.policy = policy
        self._pending: dict[str, list[tuple[T, SamplingDecision]]] = {}

    def add(
        self,
        run_id: str,
        item: T,
        *,
        status: str | None = None,
        duration_ms: float | None = None,
        terminal: bool | None = None,
    ) -> list[tuple[T, SamplingDecision]] | None:
        """Add an item and flush the run when its terminal state is known.

        ``None`` means the item remains buffered.  A list means the caller can
        persist or discard the complete run atomically according to the same
        decision.  Terminal traces use error/slow overrides before the stable
        SHA-256 rate decision.
        """
        is_terminal = (
            terminal if terminal is not None else status in self._TERMINAL_STATUSES
        )
        decision = self.policy.decide(
            trace_id=run_id,
            status=status,
            duration_ms=duration_ms,
            terminal=is_terminal,
        )
        pending = self._pending.setdefault(run_id, [])
        if not is_terminal:
            pending.append((item, decision))
            return None

        pending.append((item, decision))
        keep = decision.sampled
        reason = decision.reason if keep else "tail_rate"
        flushed = [
            (buffered, SamplingDecision(keep, reason, self.policy._score(run_id)))
            for buffered, _ in pending
        ]
        self._pending.pop(run_id, None)
        return flushed

    def flush(
        self, run_id: str, *, keep: bool = False
    ) -> list[tuple[T, SamplingDecision]]:
        """Flush an incomplete run deterministically, defaulting to discard."""
        pending = self._pending.pop(run_id, [])
        reason = "tail_timeout_keep" if keep else "tail_timeout_discard"
        score = self.policy._score(run_id)
        return [(item, SamplingDecision(keep, reason, score)) for item, _ in pending]

    @property
    def pending_runs(self) -> tuple[str, ...]:
        """Return buffered run IDs in deterministic order for observability."""
        return tuple(sorted(self._pending))

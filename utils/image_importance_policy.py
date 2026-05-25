"""Image importance gating policy for Group Chat Plus."""

from __future__ import annotations

import time
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from astrbot.api.all import logger

from .global_time_control import GlobalTimeControlManager


POLICY_VERSION = "image_importance_gate_v1"

DEBUG_MODE: bool = False


@dataclass
class ImageGateDecision:
    keep: bool
    model_importance: float
    effective_importance: float
    time_factor: float
    burst_factor: float
    batch_factor: float
    threshold: float
    gate_reason: str
    policy_version: str = POLICY_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "keep": self.keep,
            "importance": self.model_importance,
            "effective_importance": self.effective_importance,
            "time_factor": self.time_factor,
            "burst_factor": self.burst_factor,
            "batch_factor": self.batch_factor,
            "threshold": self.threshold,
            "gate_reason": self.gate_reason,
            "policy_version": self.policy_version,
        }


class ImageImportancePolicy:
    """Applies image importance, time-control, and burst-picture gating."""

    def __init__(
        self,
        *,
        enabled: bool = True,
        keep_threshold: float = 0.35,
        burst_window_seconds: int = 90,
        burst_soft_limit: int = 3,
        burst_hard_limit: int = 8,
        burst_min_factor: float = 0.15,
        batch_soft_limit: int = 2,
        batch_hard_limit: int = 6,
        batch_min_factor: float = 0.2,
        log_decisions: bool = True,
    ) -> None:
        self.enabled = bool(enabled)
        self.keep_threshold = self._clamp(float(keep_threshold), 0.0, 1.0)
        self.burst_window_seconds = max(1, int(burst_window_seconds or 90))
        self.burst_soft_limit = max(0, int(burst_soft_limit or 0))
        self.burst_hard_limit = max(
            self.burst_soft_limit + 1, int(burst_hard_limit or 0)
        )
        self.burst_min_factor = self._clamp(float(burst_min_factor), 0.0, 1.0)
        self.batch_soft_limit = max(0, int(batch_soft_limit or 0))
        self.batch_hard_limit = max(self.batch_soft_limit + 1, int(batch_hard_limit or 0))
        self.batch_min_factor = self._clamp(float(batch_min_factor), 0.0, 1.0)
        self.log_decisions = bool(log_decisions)
        self._chat_image_events: dict[str, deque[tuple[float, int]]] = defaultdict(deque)

    @classmethod
    def from_config(cls, config: dict[str, Any] | None) -> "ImageImportancePolicy":
        config = config or {}
        return cls(
            enabled=bool(config.get("enable_image_importance_gate", True)),
            keep_threshold=cls._safe_float(
                config.get("image_keep_threshold", 0.35), 0.35
            ),
            burst_window_seconds=cls._safe_int(
                config.get("image_burst_window_seconds", 90), 90
            ),
            burst_soft_limit=cls._safe_int(
                config.get("image_burst_soft_limit", 3), 3
            ),
            burst_hard_limit=cls._safe_int(
                config.get("image_burst_hard_limit", 8), 8
            ),
            burst_min_factor=cls._safe_float(
                config.get("image_burst_min_factor", 0.15), 0.15
            ),
            batch_soft_limit=cls._safe_int(
                config.get("image_batch_soft_limit", 2), 2
            ),
            batch_hard_limit=cls._safe_int(
                config.get("image_batch_hard_limit", 6), 6
            ),
            batch_min_factor=cls._safe_float(
                config.get("image_batch_min_factor", 0.2), 0.2
            ),
            log_decisions=bool(config.get("enable_image_importance_gate_log", True)),
        )

    def register_image_batch(
        self,
        *,
        chat_key: str,
        image_count: int,
        timestamp: float | None = None,
    ) -> float:
        """Record an image-bearing message and return the burst factor for it."""
        if not self.enabled:
            return 1.0
        now = float(timestamp or time.time())
        count = max(1, int(image_count or 1))
        key = str(chat_key or "unknown")
        events = self._chat_image_events[key]
        self._prune(events, now)
        recent_units = sum(units for _, units in events)
        factor = self._burst_factor(recent_units + count)
        events.append((now, count))
        return factor

    def evaluate(
        self,
        *,
        model_importance: float,
        burst_factor: float = 1.0,
        batch_factor: float = 1.0,
        quoted: bool = False,
        now: datetime | None = None,
    ) -> ImageGateDecision:
        importance = self._clamp(self._safe_float(model_importance, 0.0), 0.0, 1.0)
        time_factor = self.current_time_factor(now)
        burst_factor = self._clamp(self._safe_float(burst_factor, 1.0), 0.0, 1.0)
        batch_factor = self._clamp(self._safe_float(batch_factor, 1.0), 0.0, 1.0)

        if quoted:
            decision = ImageGateDecision(
                keep=True,
                model_importance=importance,
                effective_importance=importance,
                time_factor=1.0,
                burst_factor=1.0,
                batch_factor=1.0,
                threshold=self.keep_threshold,
                gate_reason="quoted_bypass",
            )
            return decision

        if not self.enabled:
            decision = ImageGateDecision(
                keep=True,
                model_importance=importance,
                effective_importance=importance,
                time_factor=1.0,
                burst_factor=1.0,
                batch_factor=1.0,
                threshold=self.keep_threshold,
                gate_reason="gate_disabled",
            )
            return decision

        effective = self._clamp(
            importance * time_factor * burst_factor * batch_factor, 0.0, 1.0
        )
        keep = effective >= self.keep_threshold
        reason_parts = []
        if time_factor < 1.0:
            reason_parts.append(f"time_factor={time_factor:.2f}")
        if burst_factor < 1.0:
            reason_parts.append(f"burst_factor={burst_factor:.2f}")
        if batch_factor < 1.0:
            reason_parts.append(f"batch_factor={batch_factor:.2f}")
        if not keep:
            reason_parts.append(
                f"below_threshold:{effective:.3f}<{self.keep_threshold:.3f}"
            )
        gate_reason = ";".join(reason_parts) or "kept"

        decision = ImageGateDecision(
            keep=keep,
            model_importance=importance,
            effective_importance=effective,
            time_factor=time_factor,
            burst_factor=burst_factor,
            batch_factor=batch_factor,
            threshold=self.keep_threshold,
            gate_reason=gate_reason,
        )
        return decision

    def batch_factor(self, image_count: int) -> float:
        count = max(1, int(image_count or 1))
        if self.batch_soft_limit <= 0 or count <= self.batch_soft_limit:
            return 1.0
        if count >= self.batch_hard_limit:
            return self.batch_min_factor
        span = max(1, self.batch_hard_limit - self.batch_soft_limit)
        ratio = (count - self.batch_soft_limit) / span
        return self._clamp(
            1.0 - ratio * (1.0 - self.batch_min_factor),
            self.batch_min_factor,
            1.0,
        )

    @classmethod
    def current_time_factor(cls, now: datetime | None = None) -> float:
        try:
            rule = GlobalTimeControlManager.get_current_rule(now)
            if not rule:
                return 1.0
            return cls._clamp(
                cls._safe_float(rule.get("image_importance_factor", 1.0), 1.0),
                0.0,
                1.0,
            )
        except Exception as exc:
            logger.warning("[GCP image gate] failed to read time factor: %s", exc)
            return 1.0

    def _burst_factor(self, recent_image_units: int) -> float:
        if self.burst_soft_limit <= 0 or recent_image_units <= self.burst_soft_limit:
            return 1.0
        if recent_image_units >= self.burst_hard_limit:
            return self.burst_min_factor
        span = max(1, self.burst_hard_limit - self.burst_soft_limit)
        ratio = (recent_image_units - self.burst_soft_limit) / span
        return self._clamp(
            1.0 - ratio * (1.0 - self.burst_min_factor),
            self.burst_min_factor,
            1.0,
        )

    def _prune(self, events: deque[tuple[float, int]], now: float) -> None:
        cutoff = now - self.burst_window_seconds
        while events and events[0][0] < cutoff:
            events.popleft()

    @staticmethod
    def _safe_float(value: Any, default: float) -> float:
        try:
            return float(value)
        except Exception:
            return float(default)

    @staticmethod
    def _safe_int(value: Any, default: int) -> int:
        try:
            return int(value)
        except Exception:
            return int(default)

    @staticmethod
    def _clamp(value: float, low: float, high: float) -> float:
        return max(low, min(high, float(value)))

    def _log_decision(self, decision: ImageGateDecision) -> None:
        if not self.log_decisions and not DEBUG_MODE:
            return
        logger.info(
            "[GCP image gate] keep=%s model=%.3f effective=%.3f time=%.2f burst=%.2f batch=%.2f threshold=%.3f reason=%s",
            decision.keep,
            decision.model_importance,
            decision.effective_importance,
            decision.time_factor,
            decision.burst_factor,
            decision.batch_factor,
            decision.threshold,
            decision.gate_reason,
        )

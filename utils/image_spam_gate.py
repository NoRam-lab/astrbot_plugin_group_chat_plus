"""Spam-picture gate for skipping vision calls on brush batches."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from astrbot.api.all import logger


POLICY_VERSION = "image_spam_gate_v1"


@dataclass
class ImageSpamDecision:
    skip: bool
    reason: str
    cooldown_until: float
    image_count: int
    batch_factor: float
    burst_factor: float
    sender_cooldown_active: bool
    quoted_bypass: bool
    policy_version: str = POLICY_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "skip": self.skip,
            "reason": self.reason,
            "cooldown_until": self.cooldown_until,
            "image_count": self.image_count,
            "batch_factor": self.batch_factor,
            "burst_factor": self.burst_factor,
            "sender_cooldown_active": self.sender_cooldown_active,
            "quoted_bypass": self.quoted_bypass,
            "policy_version": self.policy_version,
        }


class ImageSpamGate:
    """Detect obvious brush batches before any vision call is made."""

    def __init__(
        self,
        *,
        enabled: bool = True,
        batch_soft_limit: int = 2,
        batch_hard_limit: int = 6,
        cooldown_seconds: int = 120,
        log_decisions: bool = True,
    ) -> None:
        self.enabled = bool(enabled)
        self.batch_soft_limit = max(0, int(batch_soft_limit or 0))
        self.batch_hard_limit = max(self.batch_soft_limit + 1, int(batch_hard_limit or 0))
        self.cooldown_seconds = max(0, int(cooldown_seconds or 0))
        self.log_decisions = bool(log_decisions)
        self._sender_cooldown_until: dict[str, float] = {}

    @classmethod
    def from_config(cls, config: dict[str, Any] | None) -> "ImageSpamGate":
        config = config or {}
        return cls(
            enabled=bool(config.get("enable_image_spam_gate", True)),
            batch_soft_limit=cls._safe_int(config.get("image_spam_batch_soft_limit", 2), 2),
            batch_hard_limit=cls._safe_int(config.get("image_spam_batch_hard_limit", 6), 6),
            cooldown_seconds=cls._safe_int(config.get("image_spam_cooldown_seconds", 120), 120),
            log_decisions=bool(config.get("enable_image_importance_gate_log", True)),
        )

    def evaluate(
        self,
        *,
        chat_key: str,
        sender_id: str,
        image_count: int,
        batch_factor: float = 1.0,
        burst_factor: float = 1.0,
        quoted: bool = False,
        now: float | None = None,
    ) -> ImageSpamDecision:
        now = float(now or time.time())
        count = max(1, int(image_count or 1))
        batch_factor = self._clamp(batch_factor)
        burst_factor = self._clamp(burst_factor)

        if quoted:
            return ImageSpamDecision(
                skip=False,
                reason="quoted_bypass",
                cooldown_until=0.0,
                image_count=count,
                batch_factor=batch_factor,
                burst_factor=burst_factor,
                sender_cooldown_active=False,
                quoted_bypass=True,
            )

        if not self.enabled:
            return ImageSpamDecision(
                skip=False,
                reason="gate_disabled",
                cooldown_until=0.0,
                image_count=count,
                batch_factor=batch_factor,
                burst_factor=burst_factor,
                sender_cooldown_active=False,
                quoted_bypass=False,
            )

        sender_key = self._sender_key(chat_key, sender_id)
        cooldown_until = float(self._sender_cooldown_until.get(sender_key, 0.0) or 0.0)
        cooldown_active = cooldown_until > now
        if cooldown_active:
            reason = f"sender_cooldown:{max(1, int(cooldown_until - now))}s"
            self._log_skip(sender_key, count, batch_factor, burst_factor, reason)
            return ImageSpamDecision(
                skip=True,
                reason=reason,
                cooldown_until=cooldown_until,
                image_count=count,
                batch_factor=batch_factor,
                burst_factor=burst_factor,
                sender_cooldown_active=True,
                quoted_bypass=False,
            )

        reasons: list[str] = []
        if count >= self.batch_hard_limit:
            reasons.append(f"batch_hard_limit:{count}>={self.batch_hard_limit}")
        elif count > self.batch_soft_limit and (
            batch_factor <= 0.5 or burst_factor <= 0.5
        ):
            reasons.append(
                f"brush_like:count={count},batch={batch_factor:.2f},burst={burst_factor:.2f}"
            )

        if reasons:
            cooldown_until = now + self.cooldown_seconds if self.cooldown_seconds > 0 else now
            self._sender_cooldown_until[sender_key] = cooldown_until
            reason = ";".join(reasons)
            self._log_skip(sender_key, count, batch_factor, burst_factor, reason)
            return ImageSpamDecision(
                skip=True,
                reason=reason,
                cooldown_until=cooldown_until,
                image_count=count,
                batch_factor=batch_factor,
                burst_factor=burst_factor,
                sender_cooldown_active=False,
                quoted_bypass=False,
            )

        return ImageSpamDecision(
            skip=False,
            reason="allowed",
            cooldown_until=0.0,
            image_count=count,
            batch_factor=batch_factor,
            burst_factor=burst_factor,
            sender_cooldown_active=False,
            quoted_bypass=False,
        )

    def _log_skip(
        self,
        sender_key: str,
        image_count: int,
        batch_factor: float,
        burst_factor: float,
        reason: str,
    ) -> None:
        if not self.log_decisions:
            return
        logger.info(
            "[GCP图片刷图门] skip sender=%s count=%s batch=%.2f burst=%.2f reason=%s",
            sender_key,
            image_count,
            batch_factor,
            burst_factor,
            reason,
        )

    @staticmethod
    def _sender_key(chat_key: str, sender_id: str) -> str:
        return f"{str(chat_key or 'unknown')}:{str(sender_id or 'unknown')}"

    @staticmethod
    def _safe_int(value: Any, default: int) -> int:
        try:
            return int(value)
        except Exception:
            return int(default)

    @staticmethod
    def _clamp(value: Any) -> float:
        try:
            numeric = float(value)
        except Exception:
            numeric = 1.0
        return max(0.0, min(1.0, numeric))

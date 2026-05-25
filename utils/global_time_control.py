"""
全局时间响应控制模块。

用于按时间段统一控制：
- 普通读空气消息的最终概率系数
- @机器人 / 触发关键词 / 引用回复机器人消息 的放行概率

该模块替代旧的 TimePeriodManager 动态时间段概率调整，不依赖旧模块。
"""

from __future__ import annotations

import json
import random
from datetime import datetime
from typing import Any

from astrbot.api.all import logger


DEBUG_MODE: bool = False


class GlobalTimeControlManager:
    """全局时间响应控制管理器。"""

    _enabled: bool = False
    _rules_json: str = "[]"
    _rules: list[dict[str, Any]] = []
    _apply_to_at: bool = True
    _apply_to_keyword: bool = True
    _apply_to_reply: bool = True

    DEFAULT_RULES = [
        {
            "name": "午夜低活跃",
            "start": "00:00",
            "end": "01:00",
            "normal_probability_factor": 0.2,
            "forced_trigger_probability": 0.5,
        },
        {
            "name": "深夜休眠",
            "start": "01:00",
            "end": "08:00",
            "normal_probability_factor": 0.0,
            "forced_trigger_probability": 0.1,
        },
    ]

    @classmethod
    def initialize(cls, config: dict[str, Any] | None = None) -> None:
        config = config or {}
        cls._enabled = bool(config.get("enable_global_time_control", False))
        rules_config = config.get(
            "global_time_control_rules",
            json.dumps(cls.DEFAULT_RULES, ensure_ascii=False),
        )
        cls._rules_json = rules_config if isinstance(rules_config, list) else str(rules_config or "[]")
        cls._apply_to_at = bool(config.get("global_time_control_apply_to_at", True))
        cls._apply_to_keyword = bool(
            config.get("global_time_control_apply_to_keyword", True)
        )
        cls._apply_to_reply = bool(
            config.get("global_time_control_apply_to_reply", True)
        )
        cls._rules = cls.parse_rules(cls._rules_json)

        if DEBUG_MODE:
            logger.info(
                "[全局时间控制] 初始化完成 enabled=%s rules=%d",
                cls._enabled,
                len(cls._rules),
            )

    @classmethod
    def is_enabled(cls) -> bool:
        return bool(cls._enabled and cls._rules)

    @classmethod
    def parse_rules(cls, rules_json: str | list[dict[str, Any]] | None) -> list[dict[str, Any]]:
        if rules_json is None:
            return []

        try:
            raw_rules = rules_json
            if isinstance(rules_json, str):
                if not rules_json.strip():
                    return []
                raw_rules = json.loads(rules_json)

            if not isinstance(raw_rules, list):
                logger.warning("[全局时间控制] 规则配置不是列表，已忽略")
                return []

            parsed: list[dict[str, Any]] = []
            for idx, item in enumerate(raw_rules):
                if not isinstance(item, dict):
                    continue
                start = str(item.get("start") or "").strip()
                end = str(item.get("end") or "").strip()
                start_minutes = cls._parse_time_to_minutes(start)
                end_minutes = cls._parse_time_to_minutes(end)
                if start_minutes is None or end_minutes is None:
                    logger.warning(
                        "[全局时间控制] 第%d条规则时间格式无效 start=%s end=%s，已跳过",
                        idx + 1,
                        start,
                        end,
                    )
                    continue

                normal_factor = cls._safe_float(
                    item.get("normal_probability_factor", 1.0), 1.0
                )
                forced_prob = cls._safe_float(
                    item.get("forced_trigger_probability", 1.0), 1.0
                )
                image_factor = cls._safe_float(
                    item.get("image_importance_factor", 1.0), 1.0
                )
                normal_factor = max(0.0, normal_factor)
                forced_prob = max(0.0, min(1.0, forced_prob))
                image_factor = max(0.0, min(1.0, image_factor))

                parsed.append(
                    {
                        "name": str(item.get("name") or f"{start}-{end}"),
                        "start": start,
                        "end": end,
                        "start_minutes": start_minutes,
                        "end_minutes": end_minutes,
                        "normal_probability_factor": normal_factor,
                        "forced_trigger_probability": forced_prob,
                        "image_importance_factor": image_factor,
                    }
                )
            return parsed
        except Exception as e:
            logger.warning("[全局时间控制] 解析规则失败，已忽略: %s", e)
            return []

    @classmethod
    def get_current_rule(cls, now: datetime | None = None) -> dict[str, Any] | None:
        if not cls.is_enabled():
            return None
        now = now or datetime.now()
        current_minutes = now.hour * 60 + now.minute
        for rule in cls._rules:
            if cls._is_in_period(
                current_minutes,
                int(rule["start_minutes"]),
                int(rule["end_minutes"]),
            ):
                return rule
        return None

    @classmethod
    def adjust_normal_probability(
        cls, probability: float, now: datetime | None = None
    ) -> tuple[bool, float, str]:
        """
        调整普通读空气概率。

        Returns:
            (blocked, adjusted_probability, reason)
        """
        try:
            base_probability = max(0.0, min(1.0, float(probability)))
        except Exception:
            base_probability = 0.0

        rule = cls.get_current_rule(now)
        if not rule:
            return False, base_probability, "未命中全局时间规则"

        factor = float(rule.get("normal_probability_factor", 1.0))
        name = str(rule.get("name") or "未命名规则")
        if factor <= 0:
            return True, 0.0, f"命中{name}，普通读空气已禁用"

        adjusted = max(0.0, min(1.0, base_probability * factor))
        return (
            False,
            adjusted,
            f"命中{name}，普通概率系数×{factor:.2f}: {base_probability:.4f}->{adjusted:.4f}",
        )

    @classmethod
    def should_allow_forced_trigger(
        cls,
        trigger_type: str,
        now: datetime | None = None,
        roll: float | None = None,
    ) -> tuple[bool, str]:
        """判断强触发消息是否按当前时间段规则放行。"""
        trigger_type = str(trigger_type or "").strip().lower()
        if not cls._should_apply_to_trigger(trigger_type):
            return True, f"触发类型 {trigger_type or 'unknown'} 未启用全局时间控制"

        rule = cls.get_current_rule(now)
        if not rule:
            return True, "未命中全局时间规则"

        probability = float(rule.get("forced_trigger_probability", 1.0))
        probability = max(0.0, min(1.0, probability))
        roll_value = random.random() if roll is None else max(0.0, min(1.0, float(roll)))
        allowed = roll_value < probability
        name = str(rule.get("name") or "未命名规则")
        status = "放行" if allowed else "拦截"
        return (
            allowed,
            f"命中{name}，强触发={trigger_type}，放行概率={probability:.0%}，roll={roll_value:.4f}，{status}",
        )

    @classmethod
    def get_rules_summary(cls) -> list[str]:
        return [
            f"{r.get('name')} {r.get('start')}-{r.get('end')} "
            f"普通概率×{float(r.get('normal_probability_factor', 1.0)):.2f} "
            f"强触发放行{float(r.get('forced_trigger_probability', 1.0)):.0%}"
            f" image_factor={float(r.get('image_importance_factor', 1.0)):.2f}"
            for r in cls._rules
        ]

    @classmethod
    def _should_apply_to_trigger(cls, trigger_type: str) -> bool:
        if not cls.is_enabled():
            return False
        if trigger_type == "at":
            return cls._apply_to_at
        if trigger_type == "keyword":
            return cls._apply_to_keyword
        if trigger_type == "reply":
            return cls._apply_to_reply
        return False

    @staticmethod
    def _parse_time_to_minutes(value: str) -> int | None:
        try:
            parts = str(value).strip().split(":")
            if len(parts) < 2:
                return None
            hour = int(parts[0])
            minute = int(parts[1])
            if hour < 0 or hour > 23 or minute < 0 or minute > 59:
                return None
            return hour * 60 + minute
        except Exception:
            return None

    @staticmethod
    def _is_in_period(current: int, start: int, end: int) -> bool:
        if start == end:
            return True
        if start < end:
            return start <= current < end
        return current >= start or current < end

    @staticmethod
    def _safe_float(value: Any, default: float) -> float:
        try:
            return float(value)
        except Exception:
            return default

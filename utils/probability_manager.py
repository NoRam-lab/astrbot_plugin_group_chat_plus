"""
概率管理器模块
负责管理读空气基础概率与回复后的临时概率提升。

时间段全局控制已迁移到 global_time_control.py。
"""

import time
import asyncio
from typing import Dict, Any
from astrbot.api.all import *

# 详细日志开关（与 main.py 同款方式：单独用 if 控制）
DEBUG_MODE: bool = False

class ProbabilityManager:
    """
    概率管理器

    主要功能：
    1. 管理每个会话的读空气概率
    2. AI回复后临时提升概率
    3. 🆕 v1.1.0: 支持动态时间段概率调整
    4. 超时后自动恢复初始概率

    优先级顺序（从高到低）：
    1. 常规概率提升（回复后）
    2. 动态时间段调整
    3. 基础概率（initial_probability）
    """

    # 使用字典保存每个聊天的概率状态
    # 格式: {chat_key: {"probability": float, "boosted_until": timestamp}}
    _probability_status: Dict[str, Dict[str, Any]] = {}
    _lock = asyncio.Lock()  # 异步锁

    @staticmethod
    def initialize(config: dict | None = None):
        """初始化概率管理器。保留入口用于兼容主插件初始化流程。"""
        if DEBUG_MODE:
            logger.info("[概率管理器] 已初始化")

    @staticmethod
    def get_chat_key(platform_name: str, is_private: bool, chat_id: str) -> str:
        """
        获取聊天的唯一标识

        Args:
            platform_name: 平台名称（如aiocqhttp, gewechat等）
            is_private: 是否私聊
            chat_id: 聊天ID（群号或用户ID）

        Returns:
            唯一标识键
        """
        chat_type = "private" if is_private else "group"
        return f"{platform_name}_{chat_type}_{chat_id}"

    @staticmethod
    async def get_current_probability(
        platform_name: str, is_private: bool, chat_id: str, initial_probability: float
    ) -> float:
        """
        获取当前聊天的读空气概率

        仅处理基础概率和回复后的临时提升；全局时间控制在主流程统一应用。

        Args:
            platform_name: 平台名称
            is_private: 是否私聊
            chat_id: 聊天ID
            initial_probability: 初始概率（配置值）

        Returns:
            当前概率值（已应用当前管理器内的调整）
        """
        chat_key = ProbabilityManager.get_chat_key(platform_name, is_private, chat_id)
        current_time = time.time()

        # ========== 第一步：获取基础概率（考虑常规提升） ==========
        base_probability = initial_probability

        async with ProbabilityManager._lock:
            if chat_key in ProbabilityManager._probability_status:
                status = ProbabilityManager._probability_status[chat_key]
                boosted_until = status.get("boosted_until", 0)

                # 检查是否还在提升期内
                if current_time < boosted_until:
                    base_probability = status.get("probability", initial_probability)
                    if DEBUG_MODE:
                        logger.info(
                            f"会话 {chat_key} 使用常规提升概率: {base_probability:.2f}"
                        )
                else:
                    # 超时了，清理记录
                    del ProbabilityManager._probability_status[chat_key]
                    if DEBUG_MODE:
                        logger.info(
                            f"会话 {chat_key} 概率提升已超时，恢复为初始概率: {initial_probability:.2f}"
                        )

        # ========== 最后一步：统一安全限制（确保所有路径都返回0-1范围内的值） ==========
        # 无论前面的计算如何，最终概率必须在0.0-1.0范围内
        base_probability = max(0.0, min(1.0, base_probability))

        # ========== 返回最终概率 ==========
        return base_probability

    @staticmethod
    async def boost_probability(
        platform_name: str,
        is_private: bool,
        chat_id: str,
        boosted_probability: float,
        duration: int,
    ) -> None:
        """
        临时提升读空气概率

        AI回复后调用，提升概率促进连续对话

        Args:
            platform_name: 平台名称
            is_private: 是否私聊
            chat_id: 聊天ID
            boosted_probability: 提升后的概率
            duration: 持续时间（秒）
        """
        chat_key = ProbabilityManager.get_chat_key(platform_name, is_private, chat_id)
        current_time = time.time()
        boosted_until = current_time + duration

        async with ProbabilityManager._lock:
            ProbabilityManager._probability_status[chat_key] = {
                "probability": boosted_probability,
                "boosted_until": boosted_until,
            }

        logger.info(
            f"会话 {chat_key} 概率已提升至 {boosted_probability}, "
            f"持续 {duration} 秒 (至 {time.strftime('%H:%M:%S', time.localtime(boosted_until))})"
        )

    @staticmethod
    async def reset_probability(
        platform_name: str, is_private: bool, chat_id: str
    ) -> None:
        """
        重置概率状态

        立即清除提升状态，恢复初始概率

        Args:
            platform_name: 平台名称
            is_private: 是否私聊
            chat_id: 聊天ID
        """
        chat_key = ProbabilityManager.get_chat_key(platform_name, is_private, chat_id)

        async with ProbabilityManager._lock:
            if chat_key in ProbabilityManager._probability_status:
                del ProbabilityManager._probability_status[chat_key]
                logger.info(f"会话 {chat_key} 概率状态已重置")

    @staticmethod
    async def set_base_probability(
        platform_name: str,
        is_private: bool,
        chat_id: str,
        new_probability: float,
        duration: int = 600,
    ) -> None:
        """
        设置基础概率（用于频率动态调整）

        与 boost_probability 类似，但用于频率调整器修改基础概率
        这个概率会持续较长时间（默认10分钟），直到下次频率检查

        Args:
            platform_name: 平台名称
            is_private: 是否私聊
            chat_id: 聊天ID
            new_probability: 新的基础概率
            duration: 持续时间（秒），默认600秒（10分钟）
        """
        chat_key = ProbabilityManager.get_chat_key(platform_name, is_private, chat_id)
        current_time = time.time()
        boosted_until = current_time + duration

        async with ProbabilityManager._lock:
            ProbabilityManager._probability_status[chat_key] = {
                "probability": new_probability,
                "boosted_until": boosted_until,
            }

        logger.info(
            f"[频率调整] 会话 {chat_key} 基础概率已调整为 {new_probability:.2f}, "
            f"持续 {duration} 秒"
        )

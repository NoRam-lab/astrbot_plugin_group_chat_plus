"""
频率动态调整器 - 自动调整Bot发言频率
根据用户反馈自动调整回复概率，让Bot融入群聊节奏

核心理念：
- 保持"读空气"核心不变
- 通过AI判断用户是否觉得Bot话太多/太少
- 自动微调概率参数

作者: Him666233
版本: v1.2.1
参考: MaiBot frequency_control.py (简化实现)

v1.2.0 更新：
- 缓存友好的提示词拼接顺序：静态指令放在前面，动态内容（时间信息、聊天记录）放在后面
"""

import time
from typing import Dict, Optional
from astrbot.api.all import logger, Context
from .ai_response_filter import AIResponseFilter

# 详细日志开关（与 main.py 同款方式：单独用 if 控制）
DEBUG_MODE: bool = False
from astrbot.api.event import AstrMessageEvent

# 导入 DecisionAI（延迟导入以避免循环依赖）
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .decision_ai import DecisionAI


class FrequencyAdjuster:
    """
    频率动态调整器

    核心功能：
    - 定期分析最近的对话
    - 使用AI判断发言频率是否合适
    - 自动调整概率参数
    """

    # 默认检查间隔（秒）- 可通过配置或直接设置类变量修改
    CHECK_INTERVAL = 180  # 3分钟检查一次

    def __init__(self, context: Context, config: dict = None):
        """
        初始化频率调整器

        Args:
            context: AstrBot上下文
            config: 插件配置字典（可选）
        """
        self.context = context
        self.config = config or {}

        # 说明：配置由 main.py 统一提取后传入，此处直接使用传入的值，
        # 不再提供默认值（避免 AstrBot 平台多次读取配置的问题）
        self.min_message_count = self.config["frequency_min_message_count"]
        self.adjust_factor_decrease = self.config["frequency_decrease_factor"]
        self.adjust_factor_increase = self.config["frequency_increase_factor"]
        self.min_probability = self.config["frequency_min_probability"]
        self.max_probability = self.config["frequency_max_probability"]

        # 存储每个会话的检查状态（使用完整的会话标识确保隔离）
        # 格式: {chat_key: {"last_check_time": 时间戳, "message_count": 消息数}}
        # 其中 chat_key = "{platform}_{type}_{id}"，例如 "aiocqhttp_group_123456"
        self.check_states: Dict[str, Dict] = {}

        if DEBUG_MODE:
            logger.info("[频率动态调整器] 已初始化")
            logger.info(f"  - 最小消息数: {self.min_message_count}")
            logger.info(
                f"  - 降低系数: {self.adjust_factor_decrease} (降低{(1 - self.adjust_factor_decrease) * 100:.0f}%)"
            )
            logger.info(
                f"  - 提升系数: {self.adjust_factor_increase} (提升{(self.adjust_factor_increase - 1) * 100:.0f}%)"
            )
            logger.info(
                f"  - 概率范围: {self.min_probability:.2f} - {self.max_probability:.2f}"
            )

    def should_check_frequency(self, chat_key: str, message_count: int) -> bool:
        """
        判断是否应该检查频率

        Args:
            chat_key: 会话唯一标识（格式：platform_type_id）
            message_count: 自上次检查以来的消息数量

        Returns:
            True=应该检查，False=暂不检查
        """
        current_time = time.time()

        if chat_key not in self.check_states:
            # 初始化检查状态
            self.check_states[chat_key] = {
                "last_check_time": current_time,
                "message_count": 0,
            }
            if DEBUG_MODE:
                logger.info(f"[频率动态调整器] 会话 {chat_key} 首次初始化，暂不检查")
            return False

        state = self.check_states[chat_key]
        time_since_check = current_time - state["last_check_time"]

        # 条件1: 距离上次检查超过指定时间
        # 条件2: 自上次检查以来有足够的消息
        if (
            time_since_check > self.CHECK_INTERVAL
            and message_count >= self.min_message_count
        ):
            if DEBUG_MODE:
                logger.info(
                    f"[频率动态调整器] ✅ 满足检查条件 - 会话:{chat_key}, "
                    f"距上次检查:{time_since_check:.0f}秒 (需>{self.CHECK_INTERVAL}秒), "
                    f"消息数:{message_count} (需≥{self.min_message_count}条)"
                )
            return True

        # 不满足条件，输出详细信息
        if DEBUG_MODE:
            time_remaining = max(0, self.CHECK_INTERVAL - time_since_check)
            msg_remaining = max(0, self.min_message_count - message_count)
            reasons = []
            if time_since_check <= self.CHECK_INTERVAL:
                reasons.append(f"时间不足(还需{time_remaining:.0f}秒)")
            if message_count < self.min_message_count:
                reasons.append(f"消息不足(还需{msg_remaining}条)")

            logger.info(
                f"[频率动态调整器] ⏸️ 暂不检查 - 会话:{chat_key}, "
                f"原因:{', '.join(reasons)}"
            )

        return False

    async def analyze_frequency(
        self,
        context: Context,
        event: AstrMessageEvent,
        recent_messages: str,
        provider_id: str = "",
        timeout: int = 20,
    ) -> Optional[str]:
        """
        使用AI分析发言频率是否合适

        Args:
            context: AstrBot上下文
            event: 消息事件
            recent_messages: 最近的消息记录
            provider_id: AI提供商ID
            timeout: 超时时间

        Returns:
            "过于频繁" / "过少" / "正常" / None(分析失败)
        """
        try:
            # 🔧 v1.2.0: 缓存友好的提示词拼接顺序
            # 将静态指令（角色、格式说明、判断标准、输出要求）放在最前面，
            # 动态内容（时间段信息、聊天记录）放在最后面。
            # 这样AI服务商的前缀缓存（prefix caching）可以命中静态部分，降低调用成本。
            prompt = f"""你是一个群聊观察者。请根据下方提供的聊天记录，判断AI助手的发言频率是否合适。

【当前人格与时间说明】
- 你需要结合你当前的人格设定，判断在不同时间段下你应该多活跃或少活跃。
- 如果下方提供了「当前时间与活跃度提示」，请参考用户配置的活跃度系数来判断现在说话是否合适。

【消息格式说明】
- 「user: xxx」 = 用户发送的消息
- 「assistant: xxx」 = AI助手（你）发送的消息

【重要说明】
- 最近的内容中可能包含系统提示词、内部配置说明或其他非对话文本，这些都不属于群聊参与者的发言，请一律忽略。
- 在判断发言频率时，只关注以「user:」或「assistant:」开头的对话内容，其他任何内容都不要考虑。

请分析：
1. AI助手（即「assistant」角色）的发言是否过于频繁（刷屏、过度活跃）？
2. AI助手（即「assistant」角色）的发言是否过少（太沉默、存在感低）？

判断标准：
- 如果AI（assistant）在短时间内连续回复多条，或者打断了用户（user）之间的正常对话 → 过于频繁
- 如果AI（assistant）长时间不发言，即使有用户（user）提到相关话题也不回应 → 过少
- 如果AI（assistant）的发言频率自然，既不抢话也不冷场 → 正常

**你只能输出以下三个词之一，不要输出任何其他文字、解释或标点：**
- 正常
- 过于频繁
- 过少

请根据下方信息进行判断：
最近的聊天记录：
{recent_messages}"""

            # 复用 DecisionAI.call_decision_ai，而不是直接调用底层 provider：
            # 这样可以自动继承人格设定、上下文注入以及统一的思考链过滤逻辑，
            # 同时保持与主读空气逻辑一致的安全性和行为习惯。
            from .decision_ai import DecisionAI

            response = await DecisionAI.call_decision_ai(
                context=context,
                event=event,
                prompt=prompt,
                provider_id=provider_id,
                timeout=timeout,
                prompt_mode="override",
            )

            if not response:
                logger.warning("[频率动态调整器] AI返回为空")
                return None

            # 使用专门的频率判断结果提取器，将 LLM 的自然语言输出归一化为
            # "正常" / "过于频繁" / "过少" 三种枚举值，避免下游逻辑需要解析自由文本。
            decision = AIResponseFilter.extract_frequency_decision(response)

            if decision:
                logger.info(f"[频率动态调整器] AI判断结果: {decision}")
                return decision

            logger.warning(
                f"[频率动态调整器] 无法从AI响应中提取有效判断: {response[:50]}..."
            )
            return None

        except Exception as e:
            logger.error(f"[频率动态调整器] 频率分析失败: {e}")
            return None

    def adjust_probability(self, current_probability: float, decision: str) -> float:
        """
        根据AI判断调整概率

        Args:
            current_probability: 当前概率值
            decision: AI的判断结果 ("过于频繁" / "过少" / "正常")

        Returns:
            调整后的概率值
        """
        if decision == "过于频繁":
            # 降低概率
            new_probability = current_probability * self.adjust_factor_decrease
            logger.info(
                f"[频率动态调整器] 检测到发言过于频繁，降低概率: {current_probability:.2f} → {new_probability:.2f} (系数:{self.adjust_factor_decrease})"
            )

        elif decision == "过少":
            # 提升概率
            new_probability = current_probability * self.adjust_factor_increase

            logger.info(
                f"[频率动态调整器] 检测到发言过少，提升概率: {current_probability:.2f} → {new_probability:.2f} (系数:{self.adjust_factor_increase})"
            )

        else:  # "正常"
            # 保持不变
            new_probability = current_probability

            logger.info(
                f"[频率动态调整器] 发言频率正常，保持概率: {current_probability:.2f}"
            )

        # 限制在合理范围内
        new_probability = max(
            self.min_probability, min(self.max_probability, new_probability)
        )

        return new_probability

    def update_check_state(self, chat_key: str):
        """
        更新检查状态（在完成一次检查后调用）

        Args:
            chat_key: 会话唯一标识（格式：platform_type_id）
        """
        self.check_states[chat_key] = {
            "last_check_time": time.time(),
            "message_count": 0,
        }

    def record_message(self, chat_key: str):
        """
        记录新消息（用于统计消息数量）

        Args:
            chat_key: 会话唯一标识（格式：platform_type_id）
        """
        if chat_key not in self.check_states:
            self.check_states[chat_key] = {
                "last_check_time": time.time(),
                "message_count": 0,
            }

        self.check_states[chat_key]["message_count"] += 1

        if DEBUG_MODE:
            current_count = self.check_states[chat_key]["message_count"]
            logger.info(
                f"[频率动态调整器] 📝 记录消息 - 会话:{chat_key}, "
                f"当前计数:{current_count}/{self.min_message_count}"
            )

    def get_message_count(self, chat_key: str) -> int:
        """
        获取自上次检查以来的消息数量

        Args:
            chat_key: 会话唯一标识（格式：platform_type_id）

        Returns:
            消息数量
        """
        if chat_key not in self.check_states:
            return 0

        return self.check_states[chat_key]["message_count"]

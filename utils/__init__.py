"""
工具模块初始化
导出所有工具类供主插件使用

作者: Him666233
版本: v1.2.1
"""

from .probability_manager import ProbabilityManager
from .message_processor import MessageProcessor
from .image_handler import ImageHandler
from .image_importance_policy import ImageImportancePolicy
from .image_spam_gate import ImageSpamGate
from .context_manager import ContextManager
from .decision_ai import DecisionAI
from .reply_handler import ReplyHandler
from .reply_handler_dkq import ReplyHandlerDKQ
from .memory_injector import MemoryInjector
from .tools_reminder import ToolsReminder
from .keyword_checker import KeywordChecker
from .message_cleaner import MessageCleaner
from .attention_manager import AttentionManager

# v1.0.2 新增功能
from .mood_tracker import MoodTracker
from .frequency_adjuster import FrequencyAdjuster
from .typing_simulator import TypingSimulator

# v1.1.2 新增功能
from .ai_response_filter import AIResponseFilter

# v1.2.0 新增功能 - 拟人增强模式
from .humanize_mode import HumanizeModeManager

# v1.2.0 新增功能 - 注意力冷却机制
from .cooldown_manager import CooldownManager

# v1.2.0 新增功能 - 平台 LTM 辅助（获取平台图片描述）
from .platform_ltm_helper import PlatformLTMHelper

# SQLite-first runtime stores. They are not context history sources.
from .runtime_message_snapshot_store import RuntimeMessageSnapshotStore
from .wait_window_buffer import WaitWindowBuffer

# v1.2.0 新增功能 - 表情包检测器
from .emoji_detector import EmojiDetector, EMOJI_MARKER

# v1.2.0 新增功能 - 图片描述缓存
from .image_description_cache import ImageDescriptionCache
from .sqlite_context_store import SQLiteContextStore

# v1.2.0 新增功能 - 转发消息解析器
from .forward_message_parser import ForwardMessageParser

# 新增功能 - 新成员入群消息解析器
from .welcome_message_parser import WelcomeMessageParser

# v1.2.1 新增功能 - 回复密度管理器
from .reply_density_manager import ReplyDensityManager

# 全局时间响应控制器
from .global_time_control import GlobalTimeControlManager

# 全局调试日志开关（供各模块统一读取）
DEBUG_MODE: bool = False


def set_debug_mode(enabled: bool) -> None:
    """
    由主插件调用，统一设置调试日志开关
    所有模块应读取 utils.DEBUG_MODE 作为最终判定
    """
    global DEBUG_MODE
    DEBUG_MODE = bool(enabled)


__all__ = [
    "ProbabilityManager",
    "MessageProcessor",
    "ImageHandler",
    "ImageImportancePolicy",
    "ImageSpamGate",
    "ContextManager",
    "DecisionAI",
    "ReplyHandler",
    "ReplyHandlerDKQ",
    "MemoryInjector",
    "ToolsReminder",
    "KeywordChecker",
    "MessageCleaner",
    "AttentionManager",
    # v1.0.2 开始的新增
    "MoodTracker",
    "FrequencyAdjuster",
    "TypingSimulator",
    # v1.1.2 开始的新增
    "AIResponseFilter",
    # v1.2.0 开始的新增 - 拟人增强模式
    "HumanizeModeManager",
    # v1.2.0 开始的新增 - 注意力冷却机制
    "CooldownManager",
    # v1.2.0 开始的新增 - 平台 LTM 辅助
    "PlatformLTMHelper",
    # SQLite-first runtime stores
    "RuntimeMessageSnapshotStore",
    "WaitWindowBuffer",
    # v1.2.0 开始的新增 - 表情包检测器
    "EmojiDetector",
    "EMOJI_MARKER",
    # v1.2.0 开始的新增 - 图片描述缓存
    "ImageDescriptionCache",
    "SQLiteContextStore",
    # v1.2.0 开始的新增 - 转发消息解析器
    "ForwardMessageParser",
    # 新增 - 新成员入群消息解析器
    "WelcomeMessageParser",
    # v1.2.1 开始的新增 - 回复密度管理器
    "ReplyDensityManager",
    # 全局时间响应控制器
    "GlobalTimeControlManager",
    # 全局调试
    "DEBUG_MODE",
    "set_debug_mode",
]

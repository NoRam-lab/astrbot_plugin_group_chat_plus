"""
上下文管理器模块
负责提取和管理历史消息上下文

主要功能：
- 使用插件自有 SQLite 热库读取短期上下文
- 格式化上下文供AI使用
- 保存用户消息和bot回复
- 每条群消息即时落库，避免上下文断层
- 图片引用、图片转写状态随消息一并落盘
- 详细的保存日志便于调试

作者: Him666233
版本: v1.2.1
"""

from typing import List, Dict, Any, Optional
from pathlib import Path
from astrbot.api.all import *
from astrbot.api.message_components import Plain
import os
import asyncio
import json
import re
import time
from datetime import datetime, timezone
from .sqlite_context_store import SQLiteContextStore, StoredMessage
from ..plugin_identity import get_legacy_plugin_data_dir

# 导入 MessageCleaner（延迟导入以避免循环依赖）
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .message_cleaner import MessageCleaner
    from astrbot.core.star.context import Context
    from astrbot.core.db.po import PlatformMessageHistory

# 详细日志开关（与 main.py 同款方式：单独用 if 控制）
DEBUG_MODE: bool = False


class ContextManager:
    """
    上下文管理器

    负责历史消息的读取、保存和格式化：
    1. 从插件自有 SQLite 热库读取历史消息
    2. 控制上下文消息数量
    3. 格式化成AI可理解的文本
    """

    # 历史消息存储路径
    base_storage_path = None

    # SQLite 自有上下文存储。作为群聊短期上下文唯一来源。
    sqlite_store: Optional[SQLiteContextStore] = None

    # 自定义存储每会话最大消息数（默认500，0=禁用，-1=不限制但硬上限10000）
    custom_storage_max_messages: int = 500

    # 系统硬上限：无论如何配置，单个会话最多保存10000条消息
    CUSTOM_STORAGE_HARD_LIMIT: int = 10000

    # 历史截止时间戳：chat_id -> Unix timestamp
    # 插件重置会话时记录，读取平台历史时过滤掉该时间戳之前的消息
    _history_cutoff_timestamps: Dict[str, float] = {}
    _cutoff_file_path: Optional[Path] = None

    @staticmethod
    def init(
        data_dir: Optional[str] = None,
        custom_storage_max_messages: int = 500,
        hot_retention_days: int = 2,
        cold_retention_days: int = 90,
        cold_max_messages_per_chat: int = 50000,
        maintenance_interval_hours: float = 24.0,
        maintenance_initial_delay_seconds: float = 300.0,
    ):
        """
        初始化上下文管理器，创建存储目录

        Args:
            data_dir: 数据目录路径，如果为None则功能将受限
            custom_storage_max_messages: 自定义存储每会话最大消息数
                - 正数: 限制为该条数
                - 0: 禁用自定义存储
                - -1: 不限制（但硬上限10000）
        """
        if not data_dir:
            # 如果未提供data_dir，记录错误并禁用功能
            logger.error(
                "[上下文管理器] 未提供data_dir参数，历史消息存储功能将被禁用。"
                "请确保通过 StarTools.get_data_dir() 获取数据目录。"
            )
            ContextManager.base_storage_path = None
            return

        # 🔧 修复：统一使用 pathlib.Path 进行路径操作
        ContextManager.base_storage_path = Path(data_dir) / "chat_history"

        if not ContextManager.base_storage_path.exists():
            ContextManager.base_storage_path.mkdir(parents=True, exist_ok=True)
            if DEBUG_MODE:
                logger.info(f"上下文存储路径初始化: {ContextManager.base_storage_path}")

        # 设置自定义存储限制
        ContextManager.custom_storage_max_messages = custom_storage_max_messages
        if custom_storage_max_messages == 0:
            logger.info(
                "[上下文管理器] 历史上下文读取限制为0：不读取历史，但仍使用插件自有SQLite记录新消息"
            )
        elif custom_storage_max_messages == -1:
            logger.info(
                f"[上下文管理器] 自定义存储不限制条数（硬上限 {ContextManager.CUSTOM_STORAGE_HARD_LIMIT} 条）"
            )
        else:
            logger.info(
                f"[上下文管理器] 自定义存储每会话限制 {custom_storage_max_messages} 条消息"
            )

        # 加载持久化的历史截止时间戳
        ContextManager._load_cutoff_timestamps(data_dir)

        # 初始化 SQLite 双层上下文存储。启动异步 worker 由主插件 initialize 调用。
        ContextManager.sqlite_store = SQLiteContextStore(
            data_dir=data_dir,
            hot_retention_days=hot_retention_days,
            cold_retention_days=cold_retention_days,
            cold_max_messages_per_chat=cold_max_messages_per_chat,
            maintenance_interval_hours=maintenance_interval_hours,
            maintenance_initial_delay_seconds=maintenance_initial_delay_seconds,
        )
        logger.info(
            "[上下文管理器] 已切换为插件自有 SQLite 上下文存储 "
            f"(hot={hot_retention_days}天, cold={cold_retention_days}天/"
            f"每群{cold_max_messages_per_chat}条, "
            f"自动归档间隔={maintenance_interval_hours}小时)"
        )

    @staticmethod
    def _load_cutoff_timestamps(data_dir: Optional[str] = None) -> None:
        """从磁盘加载历史截止时间戳"""
        if not data_dir:
            return
        ContextManager._cutoff_file_path = Path(data_dir) / "history_cutoff.json"
        try:
            if ContextManager._cutoff_file_path.exists():
                with open(ContextManager._cutoff_file_path, "r", encoding="utf-8") as f:
                    ContextManager._history_cutoff_timestamps = json.load(f)
                logger.info(
                    f"[上下文管理器] 已加载 {len(ContextManager._history_cutoff_timestamps)} 个会话的历史截止时间戳"
                )
        except Exception as e:
            logger.warning(f"[上下文管理器] 加载历史截止时间戳失败: {e}")
            ContextManager._history_cutoff_timestamps = {}

    @staticmethod
    def _save_cutoff_timestamps() -> None:
        """将历史截止时间戳持久化到磁盘"""
        if not ContextManager._cutoff_file_path:
            return
        try:
            ContextManager._cutoff_file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(ContextManager._cutoff_file_path, "w", encoding="utf-8") as f:
                json.dump(
                    ContextManager._history_cutoff_timestamps, f, ensure_ascii=False
                )
        except Exception as e:
            logger.warning(f"[上下文管理器] 保存历史截止时间戳失败: {e}")

    @staticmethod
    def _session_key(platform_id: str, chat_id: str) -> str:
        return f"{platform_id}:{chat_id}"

    @staticmethod
    def _get_chat_ids(event: AstrMessageEvent) -> tuple[str, str, str, bool]:
        platform_id = str(event.get_platform_id() or "")
        is_private = event.is_private_chat()
        chat_id = event.get_group_id() if not is_private else event.get_sender_id()
        chat_id = str(chat_id or "")
        chat_type = "private" if is_private else "group"
        return platform_id, chat_id, chat_type, is_private

    @staticmethod
    def _stored_to_astr_message(
        stored: StoredMessage,
        *,
        bot_id: str,
    ) -> AstrBotMessage:
        msg = AstrBotMessage()
        msg.message_str = stored.content
        msg.platform_name = stored.platform_name
        msg.timestamp = stored.timestamp
        msg.type = (
            MessageType.GROUP_MESSAGE
            if stored.chat_type == "group"
            else MessageType.FRIEND_MESSAGE
        )
        msg.group_id = stored.chat_id if stored.chat_type == "group" else None
        msg.self_id = bot_id
        msg.session_id = stored.chat_id
        msg.message_id = stored.message_id
        msg.sender = MessageMember(
            user_id=stored.sender_id or "",
            nickname=stored.sender_name or "未知用户",
        )
        return msg

    @staticmethod
    def set_history_cutoff(chat_id: str) -> None:
        """
        设置指定会话的历史截止时间戳为当前时间。
        插件重置会话时调用，之后读取平台历史时会过滤掉此时间之前的消息。
        """
        ContextManager._history_cutoff_timestamps[chat_id] = time.time()
        ContextManager._save_cutoff_timestamps()
        logger.info(
            f"[上下文管理器] 已设置历史截止时间戳 chat_id={chat_id}, "
            f"cutoff={ContextManager._history_cutoff_timestamps[chat_id]}"
        )

    @staticmethod
    def get_history_cutoff(chat_id: str) -> float:
        """获取指定会话的历史截止时间戳，返回0表示无截止"""
        return ContextManager._history_cutoff_timestamps.get(chat_id, 0)

    @staticmethod
    def _message_to_dict(msg: AstrBotMessage) -> Dict[str, Any]:
        """
        将 AstrBotMessage 对象转换为可JSON序列化的字典

        Args:
            msg: AstrBotMessage 对象

        Returns:
            字典表示
        """
        try:
            msg_dict = {
                "message_str": msg.message_str if hasattr(msg, "message_str") else "",
                "platform_name": msg.platform_name
                if hasattr(msg, "platform_name")
                else "",
                "timestamp": msg.timestamp if hasattr(msg, "timestamp") else 0,
                "type": msg.type.value
                if hasattr(msg, "type") and hasattr(msg.type, "value")
                else "OtherMessage",
                "group_id": msg.group_id if hasattr(msg, "group_id") else None,
                "self_id": msg.self_id if hasattr(msg, "self_id") else "",
                "session_id": msg.session_id if hasattr(msg, "session_id") else "",
                "message_id": msg.message_id if hasattr(msg, "message_id") else "",
            }

            # 处理发送者信息
            if hasattr(msg, "sender") and msg.sender:
                msg_dict["sender"] = {
                    "user_id": msg.sender.user_id
                    if hasattr(msg.sender, "user_id")
                    else "",
                    "nickname": msg.sender.nickname
                    if hasattr(msg.sender, "nickname")
                    else "",
                }
            else:
                msg_dict["sender"] = None

            return msg_dict
        except Exception as e:
            logger.error(f"转换消息对象为字典失败: {e}")
            # 返回最小字典
            return {"message_str": "", "timestamp": 0}

    @staticmethod
    def _dict_to_message(msg_dict: Dict[str, Any]) -> AstrBotMessage:
        """
        将字典转换回 AstrBotMessage 对象

        Args:
            msg_dict: 消息字典

        Returns:
            AstrBotMessage 对象
        """
        try:
            msg = AstrBotMessage()
            msg.message_str = msg_dict.get("message_str", "")
            msg.platform_name = msg_dict.get("platform_name", "")
            msg.timestamp = msg_dict.get("timestamp", 0)

            # 处理消息类型
            # MessageType 是字符串枚举，值如 "GroupMessage", "FriendMessage", "OtherMessage"
            msg_type = msg_dict.get("type", "OtherMessage")
            if isinstance(msg_type, str):
                # 从字符串值创建枚举
                msg.type = MessageType(msg_type)
            elif isinstance(msg_type, int):
                # 兼容旧格式：如果是整数，映射到对应的类型
                # 这是为了处理可能存在的旧数据
                type_map = {
                    0: MessageType.OTHER_MESSAGE,
                    1: MessageType.GROUP_MESSAGE,
                    2: MessageType.FRIEND_MESSAGE,
                }
                msg.type = type_map.get(msg_type, MessageType.OTHER_MESSAGE)
            else:
                # 如果已经是 MessageType 对象，直接使用
                msg.type = msg_type

            msg.group_id = msg_dict.get("group_id")
            msg.self_id = msg_dict.get("self_id", "")
            msg.session_id = msg_dict.get("session_id", "")
            msg.message_id = msg_dict.get("message_id", "")

            # 处理发送者信息
            sender_dict = msg_dict.get("sender")
            if sender_dict:
                msg.sender = MessageMember(
                    user_id=sender_dict.get("user_id", ""),
                    nickname=sender_dict.get("nickname", ""),
                )

            return msg
        except Exception as e:
            logger.error(f"从字典转换为消息对象失败: {e}")
            # 返回一个空的消息对象而不是 None，避免后续处理出错
            empty_msg = AstrBotMessage()
            empty_msg.message_str = str(msg_dict.get("message_str", ""))
            empty_msg.timestamp = 0
            return empty_msg

    @staticmethod
    def _get_storage_path(platform_name: str, is_private: bool, chat_id: str) -> Path:
        """
        获取历史消息的本地存储路径

        Args:
            platform_name: 平台名称
            is_private: 是否私聊
            chat_id: 聊天ID

        Returns:
            JSON文件路径（Path对象），如果 base_storage_path 未初始化则返回 None
        """
        if not ContextManager.base_storage_path:
            # 🔧 修复：尝试使用 StarTools 获取数据目录进行初始化
            try:
                from astrbot.core.star.star_tools import StarTools

                data_dir = get_legacy_plugin_data_dir(StarTools)
                if data_dir:
                    ContextManager.init(str(data_dir))
                else:
                    logger.warning(
                        "[上下文管理器] 无法获取数据目录，_get_storage_path 返回 None"
                    )
                    return None
            except Exception as e:
                logger.warning(f"[上下文管理器] 初始化存储路径失败: {e}")
                return None

        # 再次检查，确保初始化成功
        if not ContextManager.base_storage_path:
            logger.warning(
                "[上下文管理器] base_storage_path 仍为 None，_get_storage_path 返回 None"
            )
            return None

        # 🔧 修复：统一使用 pathlib.Path 进行路径操作
        chat_type = "private" if is_private else "group"
        directory = ContextManager.base_storage_path / platform_name / chat_type

        if not directory.exists():
            directory.mkdir(parents=True, exist_ok=True)

        return directory / f"{chat_id}.json"

    @staticmethod
    def _get_effective_storage_limit() -> int:
        """
        获取有效的自定义存储限制条数

        Returns:
            有效的最大消息条数（已处理-1和硬上限）
        """
        limit = ContextManager.custom_storage_max_messages
        if limit == 0:
            return 0
        elif limit == -1:
            return ContextManager.CUSTOM_STORAGE_HARD_LIMIT
        else:
            return min(limit, ContextManager.CUSTOM_STORAGE_HARD_LIMIT)

    @staticmethod
    def _count_messages_in_file(file_path: Path) -> int:
        """
        统计JSON数组文件中的消息条数（不加载整个文件到内存）

        利用 json.dump(indent=2) 产生的格式特征：
        每个顶层数组元素（消息字典）以 '  {' 开头（恰好2个空格+左花括号）。
        逐行扫描统计这种行的数量即可得到消息条数。

        Args:
            file_path: JSON文件路径

        Returns:
            消息条数（文件不存在或出错返回0）
        """
        count = 0
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    # indent=2 格式下，顶层数组元素的开头行恰好是 "  {"
                    if line.startswith("  {"):
                        count += 1
        except (FileNotFoundError, IOError, OSError):
            pass
        return count

    @staticmethod
    def _trim_messages_in_file(file_path: Path, keep_count: int) -> bool:
        """
        裁剪JSON数组文件，只保留最新的 keep_count 条消息（不加载整个文件到内存）

        使用两遍扫描法：
        1. 第一遍：统计总消息数
        2. 第二遍：逐行读取，跳过需要丢弃的旧消息，将保留的消息直接写入临时文件
        最后用临时文件替换原文件。

        整个过程内存占用为 O(单行大小)，不会随消息总数增长。

        Args:
            file_path: JSON文件路径
            keep_count: 要保留的消息条数

        Returns:
            是否执行了裁剪
        """
        if keep_count <= 0:
            # 删除整个文件
            try:
                if file_path.exists():
                    file_path.unlink()
                    if DEBUG_MODE:
                        logger.info(f"[自定义存储裁剪] 已删除文件: {file_path}")
                return True
            except Exception as e:
                logger.error(f"[自定义存储裁剪] 删除文件失败: {e}")
                return False

        # 第一遍：统计消息总数
        total = ContextManager._count_messages_in_file(file_path)
        if total <= keep_count:
            return False  # 未超出限制，无需裁剪

        skip_count = total - keep_count

        # 第二遍：逐行处理，跳过前 skip_count 条消息，保留剩余消息
        temp_path = file_path.with_suffix(".tmp")
        try:
            message_index = 0  # 当前处于第几条消息（从1开始）

            with (
                open(file_path, "r", encoding="utf-8") as src,
                open(temp_path, "w", encoding="utf-8") as dst,
            ):
                dst.write("[\n")

                for line in src:
                    # 检测消息开始（indent=2下顶层元素以 "  {" 开头）
                    if line.startswith("  {"):
                        message_index += 1

                    # 跳过数组的开闭括号（我们自己写）
                    stripped = line.rstrip("\n\r")
                    if stripped == "[" or stripped == "]":
                        continue

                    # 只写入保留的消息（第 skip_count+1 条及之后）
                    if message_index > skip_count:
                        dst.write(line)

                dst.write("]\n")

            # 替换原文件（Windows下需先删除原文件才能重命名）
            file_path.unlink()
            temp_path.rename(file_path)

            logger.info(
                f"[自定义存储裁剪] 裁剪完成: {total} → {keep_count} 条（丢弃最旧的 {skip_count} 条）"
            )
            return True

        except Exception as e:
            # 清理临时文件
            try:
                if temp_path.exists():
                    temp_path.unlink()
            except Exception:
                pass
            logger.error(f"[自定义存储裁剪] 裁剪文件失败: {e}")
            return False

    @staticmethod
    def _append_message_to_file(file_path: Path, message_dict: dict) -> bool:
        """
        向JSON数组文件追加一条消息（不加载整个文件到内存）

        通过文件末尾定位找到 ']' 的位置，直接在该位置插入新消息。
        内存占用只与单条消息大小相关，不随文件大小增长。

        Args:
            file_path: JSON文件路径
            message_dict: 要追加的消息字典

        Returns:
            是否成功
        """
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)

            if not file_path.exists() or file_path.stat().st_size == 0:
                # 文件不存在或为空，创建新文件
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump([message_dict], f, ensure_ascii=False, indent=2)
                return True

            # 格式化新消息（缩进2空格，与数组内元素对齐）
            msg_json = json.dumps(message_dict, ensure_ascii=False, indent=2)
            indented_lines = []
            for line in msg_json.split("\n"):
                indented_lines.append("  " + line)
            indented_msg = "\n".join(indented_lines)

            # 定位文件末尾的 ']' 并替换
            with open(file_path, "r+", encoding="utf-8") as f:
                # 从文件末尾向前搜索 ']'
                f.seek(0, 2)  # 移到文件末尾
                file_size = f.tell()

                pos = file_size - 1
                while pos >= 0:
                    f.seek(pos)
                    char = f.read(1)
                    if char == "]":
                        break
                    pos -= 1

                if pos < 0:
                    # 找不到 ']'，文件格式损坏，重新创建
                    f.seek(0)
                    json.dump([message_dict], f, ensure_ascii=False, indent=2)
                    f.truncate()
                    return True

                # 检查数组是否有内容（']' 前面是否有非空白、非 '[' 的字符）
                check_pos = pos - 1
                has_content = False
                while check_pos >= 0:
                    f.seek(check_pos)
                    char = f.read(1)
                    if not char.isspace():
                        has_content = char != "["
                        break
                    check_pos -= 1

                # 在 ']' 的位置写入新消息
                f.seek(pos)
                if has_content:
                    f.write(",\n" + indented_msg + "\n]")
                else:
                    f.write("\n" + indented_msg + "\n]")
                f.truncate()

            return True

        except Exception as e:
            logger.error(f"[自定义存储] 追加消息失败: {e}")
            # 追加失败时尝试回退到完整写入
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump([message_dict], f, ensure_ascii=False, indent=2)
                return True
            except Exception:
                return False

    @staticmethod
    def _clear_all_custom_storage():
        """
        清理所有自定义存储文件（当配置为0即禁用自定义存储时调用）
        """
        if (
            not ContextManager.base_storage_path
            or not ContextManager.base_storage_path.exists()
        ):
            return

        try:
            deleted_count = 0
            for json_file in ContextManager.base_storage_path.rglob("*.json"):
                try:
                    json_file.unlink()
                    deleted_count += 1
                except Exception as e:
                    logger.warning(f"[自定义存储] 删除文件失败 {json_file}: {e}")

            if deleted_count > 0:
                logger.info(
                    f"[自定义存储] 已清理 {deleted_count} 个自定义存储文件（配置为禁用自定义存储）"
                )
        except Exception as e:
            logger.error(f"[自定义存储] 清理自定义存储失败: {e}")

    @staticmethod
    def _is_custom_storage_enabled() -> bool:
        """检查自定义存储是否启用"""
        return ContextManager.custom_storage_max_messages != 0

    @staticmethod
    def get_history_messages(
        event: AstrMessageEvent, max_messages: int
    ) -> List[AstrBotMessage]:
        """
        获取历史消息记录

        Args:
            event: 消息事件对象
            max_messages: 最大消息数量
                - 正数: 限制条数
                - 0: 不获取
                - -1: 不限制

        Returns:
            历史消息列表
        """
        try:
            platform_id = event.get_platform_id()
            is_private = event.is_private_chat()
            chat_id = event.get_group_id() if not is_private else event.get_sender_id()
            if not chat_id or not ContextManager.sqlite_store:
                return []
            return asyncio.run(
                ContextManager.get_history_messages_by_params_with_fallback(
                    platform_name=event.get_platform_name(),
                    platform_id=platform_id,
                    is_private=is_private,
                    chat_id=str(chat_id),
                    bot_id=event.get_self_id(),
                    max_messages=max_messages,
                    context=None,
                    cached_messages=[],
                )
            )
        except RuntimeError:
            logger.warning("同步历史获取在事件循环中不可用，请改用异步接口")
            return []
        except Exception as e:
            logger.error(f"读取历史消息失败: {e}")
            return []

    @staticmethod
    def get_history_messages_by_params(
        platform_name: str,
        is_private: bool,
        chat_id: str,
        max_messages: int,
    ) -> List[AstrBotMessage]:
        """
        根据参数获取历史消息记录（无需event对象）

        Args:
            platform_name: 平台名称
            is_private: 是否私聊
            chat_id: 聊天ID
            max_messages: 最大消息数量
                - 正数: 限制条数
                - 0: 不获取
                - -1: 不限制

        Returns:
            历史消息列表
        """
        try:
            if not chat_id or not ContextManager.sqlite_store:
                return []
            rows = asyncio.run(
                ContextManager.sqlite_store.get_recent_messages(
                    platform_id=platform_name,
                    chat_id=str(chat_id),
                    limit=max_messages,
                    include_cold=False,
                )
            )
            bot_id = ""
            history = [
                ContextManager._stored_to_astr_message(row, bot_id=bot_id)
                for row in rows
            ]
            if DEBUG_MODE:
                logger.info(
                    f"[SQLite历史-params] 读取历史消息 {len(history)} 条 chat_id={chat_id}"
                )
            return history
        except RuntimeError:
            logger.warning("同步历史获取在事件循环中不可用，请改用异步接口")
            return []
        except Exception as e:
            logger.error(f"读取历史消息失败: {e}")
            return []

    @staticmethod
    def _official_history_to_message(
        history_item: "PlatformMessageHistory",
        platform_name: str,
        is_private: bool,
        chat_id: str,
        bot_id: str,
    ) -> Optional[AstrBotMessage]:
        """
        将官方 PlatformMessageHistory 对象转换为 AstrBotMessage

        Args:
            history_item: 官方历史记录对象
            platform_name: 平台名称
            is_private: 是否私聊
            chat_id: 聊天ID
            bot_id: 机器人ID

        Returns:
            AstrBotMessage 对象，转换失败返回 None
        """
        try:
            msg = AstrBotMessage()

            # 从 content 字段提取消息文本
            # content 是一个消息链列表，格式如 [{"type": "text", "data": {"text": "..."}}]
            content = history_item.content
            message_text = ""
            if isinstance(content, list):
                for comp in content:
                    if isinstance(comp, dict):
                        comp_type = comp.get("type", "")
                        comp_data = comp.get("data", {})
                        if comp_type == "text" and isinstance(comp_data, dict):
                            message_text += comp_data.get("text", "")
            elif isinstance(content, dict):
                # 兼容单个组件的情况
                comp_type = content.get("type", "")
                comp_data = content.get("data", {})
                if comp_type == "text" and isinstance(comp_data, dict):
                    message_text = comp_data.get("text", "")

            msg.message_str = message_text
            msg.platform_name = platform_name

            # 处理时间戳
            if hasattr(history_item, "created_at") and history_item.created_at:
                if isinstance(history_item.created_at, datetime):
                    msg.timestamp = int(history_item.created_at.timestamp())
                else:
                    msg.timestamp = 0
            else:
                msg.timestamp = 0

            # 设置消息类型
            msg.type = (
                MessageType.FRIEND_MESSAGE if is_private else MessageType.GROUP_MESSAGE
            )

            if not is_private:
                msg.group_id = chat_id

            # 设置发送者信息
            sender_id = history_item.sender_id or ""
            sender_name = history_item.sender_name or "未知用户"
            msg.sender = MessageMember(user_id=sender_id, nickname=sender_name)
            msg.self_id = bot_id
            msg.session_id = chat_id
            msg.message_id = f"official_{history_item.id}" if history_item.id else ""

            return msg

        except Exception as e:
            if DEBUG_MODE:
                logger.warning(f"转换官方历史记录失败: {e}")
            return None

    @staticmethod
    async def get_history_messages_with_fallback(
        event: AstrMessageEvent,
        max_messages: int,
        context: "Context" = None,
        cached_messages: List[AstrBotMessage] = None,
    ) -> List[AstrBotMessage]:
        """
        获取历史消息记录。

        新策略：
        1. 只读取 group_chat_plus 自有 SQLite 热库。
        2. 不读取 AstrBot 官方 message_history_manager / conversation_manager。
        3. cached_messages 参数仅为旧版本兼容保留，不再参与 prompt 构建。

        Args:
            event: 消息事件对象
            max_messages: 最大消息数量
                - 正数: 限制条数
                - 0: 不获取
                - -1: 不限制
            context: Context 对象（兼容参数，不读取官方存储）
            cached_messages: 已废弃兼容参数，内部忽略

        Returns:
            历史消息列表（已按时间排序，只来自插件 SQLite）
        """
        try:
            # 🔧 修复：确保 max_messages 是整数类型
            if not isinstance(max_messages, int):
                try:
                    max_messages = int(max_messages)
                except (ValueError, TypeError):
                    logger.warning(
                        f"⚠️ max_messages 值 '{max_messages}' 无法转换为整数，使用默认值 -1"
                    )
                    max_messages = -1

            # 如果配置为0,不获取历史消息
            if max_messages == 0:
                if DEBUG_MODE:
                    logger.info("配置为不获取历史消息")
                return []

            # 获取平台和聊天信息
            platform_name = event.get_platform_name()
            platform_id = event.get_platform_id()
            is_private = event.is_private_chat()
            chat_id = event.get_group_id() if not is_private else event.get_sender_id()
            bot_id = event.get_self_id()

            if not chat_id:
                logger.warning("无法获取聊天ID,跳过历史消息提取")
                return []

            # 硬上限保护
            HARD_LIMIT = 500
            if max_messages == -1:
                effective_limit = HARD_LIMIT
            else:
                effective_limit = min(max_messages, HARD_LIMIT)

            history: List[AstrBotMessage] = []

            # ========== 1. 只从插件自有 SQLite 读取 ==========
            if ContextManager.sqlite_store:
                rows = await ContextManager.sqlite_store.get_recent_messages(
                    platform_id=str(platform_id or ""),
                    chat_id=str(chat_id),
                    limit=effective_limit,
                    include_cold=False,
                )
                history = [
                    ContextManager._stored_to_astr_message(row, bot_id=bot_id)
                    for row in rows
                    if row.content
                ]
                cutoff_ts = ContextManager.get_history_cutoff(str(chat_id))
                if cutoff_ts > 0 and history:
                    before_count = len(history)
                    history = [
                        m
                        for m in history
                        if (getattr(m, "timestamp", 0) or 0) >= cutoff_ts
                    ]
                    filtered = before_count - len(history)
                    if filtered > 0:
                        logger.info(
                            f"[上下文管理器] SQLite历史截止过滤: 丢弃 {filtered} 条旧消息 "
                            f"(cutoff={cutoff_ts}, chat_id={chat_id})"
                        )
                if DEBUG_MODE:
                    logger.info(
                        f"[上下文管理器] 从插件自有热库读取到 {len(history)} 条历史消息"
                    )
            else:
                logger.warning("[上下文管理器] SQLite存储未初始化，无法读取历史")

            # ========== 2. 按时间排序并截断 ==========
            # 按时间戳排序
            history.sort(
                key=lambda m: (
                    m.timestamp if hasattr(m, "timestamp") and m.timestamp else 0
                )
            )

            # 截断到有效限制
            if len(history) > effective_limit:
                history = history[-effective_limit:]

            logger.info(f"[上下文管理器] 最终获取插件自有历史消息 {len(history)} 条")
            return history

        except Exception as e:
            logger.error(f"[上下文管理器] 获取历史消息失败: {e}")
            return []

    @staticmethod
    async def get_history_messages_by_params_with_fallback(
        platform_name: str,
        platform_id: str,
        is_private: bool,
        chat_id: str,
        bot_id: str,
        max_messages: int,
        context: "Context" = None,
        cached_messages: List[AstrBotMessage] = None,
    ) -> List[AstrBotMessage]:
        """
        根据参数获取历史消息记录。
        只读取 group_chat_plus 自有 SQLite 存储，不读取 AstrBot 官方历史。

        Args:
            platform_name: 平台名称
            platform_id: 平台ID
            is_private: 是否私聊
            chat_id: 聊天ID
            bot_id: 机器人ID
            max_messages: 最大消息数量
            context: Context 对象（兼容参数，不读取官方存储）
            cached_messages: 已废弃兼容参数，内部忽略

        Returns:
            历史消息列表
        """
        try:
            # 🔧 修复：确保 max_messages 是整数类型
            if not isinstance(max_messages, int):
                try:
                    max_messages = int(max_messages)
                except (ValueError, TypeError):
                    logger.warning(
                        f"⚠️ max_messages 值 '{max_messages}' 无法转换为整数，使用默认值 -1"
                    )
                    max_messages = -1

            # 如果配置为0,不获取历史消息
            if max_messages == 0:
                return []

            if not chat_id:
                logger.warning("无法获取聊天ID,跳过历史消息提取")
                return []

            # 硬上限保护
            HARD_LIMIT = 500
            if max_messages == -1:
                effective_limit = HARD_LIMIT
            else:
                effective_limit = min(max_messages, HARD_LIMIT)

            history: List[AstrBotMessage] = []

            # ========== 1. 只从插件自有 SQLite 读取 ==========
            if ContextManager.sqlite_store:
                rows = await ContextManager.sqlite_store.get_recent_messages(
                    platform_id=str(platform_id or ""),
                    chat_id=str(chat_id),
                    limit=effective_limit,
                    include_cold=False,
                )
                history = [
                    ContextManager._stored_to_astr_message(row, bot_id=bot_id)
                    for row in rows
                    if row.content
                ]
                cutoff_ts = ContextManager.get_history_cutoff(str(chat_id))
                if cutoff_ts > 0 and history:
                    before_count = len(history)
                    history = [
                        m
                        for m in history
                        if (getattr(m, "timestamp", 0) or 0) >= cutoff_ts
                    ]
                    filtered = before_count - len(history)
                    if filtered > 0:
                        logger.info(
                            f"[上下文管理器] SQLite历史截止过滤: 丢弃 {filtered} 条旧消息 "
                            f"(cutoff={cutoff_ts}, chat_id={chat_id})"
                        )
                if DEBUG_MODE:
                    logger.info(
                        f"[上下文管理器] 从插件自有热库读取到 {len(history)} 条历史消息"
                    )
            else:
                logger.warning("[上下文管理器] SQLite存储未初始化，无法读取历史")

            # ========== 2. 按时间排序并截断 ==========
            history.sort(
                key=lambda m: (
                    m.timestamp if hasattr(m, "timestamp") and m.timestamp else 0
                )
            )

            if len(history) > effective_limit:
                history = history[-effective_limit:]

            return history

        except Exception as e:
            logger.error(f"[上下文管理器] 获取历史消息失败: {e}")
            return []

    @staticmethod
    async def format_context_for_ai(
        history_messages: List[AstrBotMessage],
        current_message: str,
        bot_id: str,
        include_timestamp: bool = True,
        include_sender_info: bool = True,
        window_buffered_messages: list = None,
    ) -> str:
        """
        将历史消息格式化为AI可理解的文本

        Args:
            history_messages: 历史消息列表
            current_message: 当前消息
            bot_id: 机器人ID，用于识别自己的回复
            include_timestamp: 是否包含时间戳（默认为True）
            include_sender_info: 是否包含发送者信息（默认为True）
            window_buffered_messages: 窗口缓冲消息列表（用于拼接到当前消息下方）

        Returns:
            格式化后的文本
        """
        try:
            formatted_parts = []

            # 如果有历史消息,添加历史消息部分
            if history_messages:
                if include_sender_info:
                    formatted_parts.append(
                        f"=== 历史消息上下文 ===\n"
                        f"[重要提示] 以下每条历史消息均已标注发送者的名字和用户ID（格式：名字(ID:用户ID): 消息内容）。\n"
                        f"其中 ID 为 {bot_id} 的消息是【你自己之前发出的回复】（前缀标有「【禁止重复-你的历史回复】」），你已经说过这些话了，绝对不能再重复相同或相似的内容。\n"
                        f"其余 ID 的消息是【其他用户发送的消息】，是别人说的话，不是你说的。\n"
                        f"群聊中可能有多个不同用户的发言，请仔细识别每条消息的发送者 ID，准确区分是谁在说话，不要混淆。"
                    )
                else:
                    formatted_parts.append(
                        "=== 历史消息上下文 ===\n"
                        "[重要提示] 以下历史消息中，前缀标有「【禁止重复-你的历史回复】」的消息是【你自己之前发出的回复】，你已经说过这些话了，绝对不能再重复。\n"
                        "其余消息均为【其他用户发送的消息】，是别人说的话，不是你说的。请仔细区分。"
                    )

                for msg in history_messages:
                    # 跳过无效的消息对象
                    if msg is None or not isinstance(msg, AstrBotMessage):
                        logger.warning(f"跳过无效的历史消息对象: {type(msg)}")
                        continue
                    # 获取发送者信息（如果需要）
                    sender_name = "未知用户"
                    sender_id = "unknown"
                    is_bot = False

                    if hasattr(msg, "sender") and msg.sender:
                        sender_name = msg.sender.nickname or "未知用户"
                        sender_id = msg.sender.user_id or "unknown"
                        # 判断是否是机器人自己的消息
                        # 确保类型一致性：统一转换为字符串进行比较
                        is_bot = str(sender_id) == str(bot_id)

                        # 调试日志（仅在第一条消息时输出，避免刷屏）
                        if formatted_parts and len(formatted_parts) == 1:
                            if DEBUG_MODE:
                                logger.info(
                                    f"[上下文格式化] 机器人ID: {bot_id}, 当前消息发送者ID: {sender_id}, 是否为机器人: {is_bot}"
                                )

                    # 如果还没有判定为bot，尝试通过 self_id 判断
                    # 有时候消息没有正确的sender，但有self_id
                    if not is_bot and hasattr(msg, "self_id") and msg.self_id:
                        # 如果消息的 self_id 等于当前 bot_id，说明这是机器人发出的消息
                        # 但需要注意：self_id 通常表示"当前机器人的ID"
                        # 对于bot发送的消息，sender.user_id 应该等于 self_id
                        pass

                    # 获取消息时间（如果需要）
                    time_str = ""
                    if include_timestamp:
                        time_str = "未知时间"
                        if hasattr(msg, "timestamp") and msg.timestamp:
                            try:
                                dt = datetime.fromtimestamp(msg.timestamp)
                                weekday_names = [
                                    "周一",
                                    "周二",
                                    "周三",
                                    "周四",
                                    "周五",
                                    "周六",
                                    "周日",
                                ]
                                weekday = weekday_names[dt.weekday()]
                                time_str = dt.strftime(f"%Y-%m-%d {weekday} %H:%M:%S")
                            except:
                                pass

                    # 获取消息内容
                    message_content = ""
                    if hasattr(msg, "message_str"):
                        message_content = msg.message_str
                    elif hasattr(msg, "message"):
                        # 简单提取文本
                        for comp in msg.message:
                            if isinstance(comp, Plain):
                                message_content += comp.text

                    # 格式化消息（根据配置决定格式）
                    # 构建消息前缀部分
                    prefix_parts = []

                    # 添加时间戳（如果启用，且不是bot自己的消息，避免AI模仿时间戳格式）
                    if include_timestamp and time_str and not is_bot:
                        prefix_parts.append(f"[{time_str}]")

                    # 添加发送者信息（如果启用）
                    if include_sender_info:
                        if is_bot:
                            # AI自己的回复，醒目标注防止重复
                            prefix_parts.append(
                                f"【禁止重复-你的历史回复】{sender_name}(ID:{sender_id}):"
                            )
                        else:
                            # 其他用户的消息
                            prefix_parts.append(f"{sender_name}(ID:{sender_id}):")
                    else:
                        # 不包含发送者信息时，仍需要区分bot自己的消息
                        if is_bot:
                            prefix_parts.append("【禁止重复-你的历史回复】:")

                    # 组合完整消息
                    if prefix_parts:
                        formatted_msg = " ".join(prefix_parts) + " " + message_content
                    else:
                        formatted_msg = message_content

                    formatted_parts.append(formatted_msg)

                formatted_parts.append("")  # 空行分隔

            # 添加当前消息部分（强调重要性）
            formatted_parts.append("")  # 空行分隔
            formatted_parts.append("=" * 50)
            formatted_parts.append(
                "=== 以上全部是历史消息，你已经处理过了，不要重复回答 ==="
            )
            formatted_parts.append(
                "=== 【重要】以下是当前新消息（请优先关注这条消息的核心内容）==="
            )
            formatted_parts.append("=" * 50)
            formatted_parts.append(current_message)
            formatted_parts.append("=" * 50)

            # 窗口缓冲消息区域（当前消息之后紧接着发的消息）
            try:
                if window_buffered_messages:
                    formatted_parts.append("")
                    formatted_parts.append(
                        "--- 以下是你收到这条消息后，同一用户或其他用户紧接着又发的消息 ---"
                    )
                    formatted_parts.append(
                        "这些消息不一定是对你说的，请自行参考判断是否需要在回复中一并考虑。"
                    )
                    formatted_parts.append(
                        "重要：这些追加消息的发送者可能与当前对话对象不同，请根据每条消息的发送者名字和ID仔细区分。"
                    )

                    # 按时间排序
                    sorted_wb = sorted(
                        window_buffered_messages,
                        key=lambda m: (
                            m.get("message_timestamp") or m.get("timestamp", 0)
                        ),
                    )

                    for wb_msg in sorted_wb:
                        wb_sender_name = wb_msg.get("sender_name", "未知用户")
                        wb_sender_id = wb_msg.get("sender_id", "unknown")
                        wb_content = wb_msg.get("content", "")

                        # 时间格式化（与历史消息保持一致）
                        wb_time_str = ""
                        if include_timestamp:
                            msg_ts = wb_msg.get("message_timestamp") or wb_msg.get(
                                "timestamp"
                            )
                            if msg_ts:
                                try:
                                    dt = datetime.fromtimestamp(msg_ts)
                                    weekday_names = [
                                        "周一",
                                        "周二",
                                        "周三",
                                        "周四",
                                        "周五",
                                        "周六",
                                        "周日",
                                    ]
                                    weekday = weekday_names[dt.weekday()]
                                    wb_time_str = f"[{dt.strftime(f'%Y-%m-%d {weekday} %H:%M:%S')}] "
                                except Exception:
                                    pass

                        if include_sender_info:
                            formatted_parts.append(
                                f"{wb_time_str}{wb_sender_name}(ID:{wb_sender_id}): {wb_content}"
                            )
                        else:
                            formatted_parts.append(f"{wb_time_str}{wb_content}")

                    formatted_parts.append("--- 以上为紧接着的追加消息 ---")

                    if DEBUG_MODE:
                        logger.info(
                            f"[上下文格式化] 已拼接 {len(sorted_wb)} 条窗口缓冲消息到当前消息下方"
                        )
            except Exception as e:
                logger.warning(f"[上下文格式化] 窗口缓冲消息拼接失败，降级忽略: {e}")

            result = "\n".join(formatted_parts)
            if DEBUG_MODE:
                logger.info(f"上下文格式化完成,总长度: {len(result)} 字符")
            return result

        except Exception as e:
            logger.error(f"格式化上下文时发生错误: {e}")
            # 发生错误时,至少返回当前消息
            return current_message

    @staticmethod
    def calculate_context_size(
        history_messages: List[AstrBotMessage], current_message: str
    ) -> int:
        """
        计算上下文总消息数（含当前消息）

        Args:
            history_messages: 历史消息列表
            current_message: 当前消息

        Returns:
            总消息数
        """
        return len(history_messages) + 1

    @staticmethod
    async def save_user_message(
        event: AstrMessageEvent, message_text: str, context: "Context" = None
    ) -> bool:
        """
        保存用户消息到插件自有 SQLite。

        Args:
            event: 消息事件
            message_text: 用户消息（可能已包含元数据）
            context: Context对象（可选）

        Returns:
            是否成功
        """
        try:
            from .message_cleaner import MessageCleaner

            cleaned_message = MessageCleaner.clean_message(message_text) or message_text
            platform_id, chat_id, chat_type, _ = ContextManager._get_chat_ids(event)
            if not chat_id:
                logger.warning("无法获取聊天ID,跳过消息保存")
                return False
            if not ContextManager.sqlite_store:
                logger.warning("[上下文管理器] SQLite存储未初始化，用户消息未保存")
                return False

            msg_ts = None
            try:
                msg_ts = getattr(event.message_obj, "timestamp", None)
            except Exception:
                msg_ts = None
            try:
                msg_id = getattr(event.message_obj, "message_id", None)
            except Exception:
                msg_id = None
            image_meta = {}
            try:
                image_meta = event.get_extra("gcp_image_meta", {}) or {}
            except Exception:
                image_meta = {}

            payload = {
                "message_id": str(msg_id or f"user_{time.time_ns()}"),
                "platform_name": event.get_platform_name(),
                "platform_id": platform_id,
                "chat_id": chat_id,
                "chat_key": ContextManager._session_key(platform_id, chat_id),
                "chat_type": chat_type,
                "role": "user",
                "sender_id": event.get_sender_id(),
                "sender_name": event.get_sender_name() or "未知用户",
                "timestamp": float(msg_ts or time.time()),
                "content": cleaned_message,
                "reply_to_message_id": "",
                "image_refs": image_meta.get("image_refs") or [],
                "image_descriptions": image_meta.get("image_descriptions") or [],
                "image_status": image_meta.get("image_status") or "",
                "image_items": image_meta.get("image_items") or [],
                "image_policy_version": image_meta.get("policy_version") or "",
            }
            ok = await ContextManager.sqlite_store.add_message_sync(payload)
            if ok:
                logger.info("[GCP上下文存储] 用户消息已落盘 chat_id=%s", chat_id)
            return ok
        except Exception as e:
            logger.error(f"保存用户消息失败: {e}", exc_info=True)
            return False

    @staticmethod
    async def save_cached_user_message(
        event: AstrMessageEvent,
        cached_msg: dict,
        *,
        source: str = "",
    ) -> bool:
        """保存待回复/未回复消息到插件自有 SQLite。"""
        try:
            if not isinstance(cached_msg, dict):
                return False
            content = cached_msg.get("content") or ""
            if not content:
                return False
            from .message_cleaner import MessageCleaner

            content = MessageCleaner.clean_message(content) or content
            platform_id, chat_id, chat_type, _ = ContextManager._get_chat_ids(event)
            if not chat_id or not ContextManager.sqlite_store:
                return False
            ts = cached_msg.get("message_timestamp") or cached_msg.get("timestamp")
            try:
                ts = float(ts or time.time())
            except Exception:
                ts = time.time()
            payload = {
                "message_id": str(
                    cached_msg.get("message_id") or f"cached_{time.time_ns()}"
                ),
                "platform_name": event.get_platform_name(),
                "platform_id": platform_id,
                "chat_id": chat_id,
                "chat_key": ContextManager._session_key(platform_id, chat_id),
                "chat_type": chat_type,
                "role": "user",
                "sender_id": cached_msg.get("sender_id") or event.get_sender_id(),
                "sender_name": cached_msg.get("sender_name")
                or event.get_sender_name()
                or "未知用户",
                "timestamp": ts,
                "content": content,
                "reply_to_message_id": cached_msg.get("reply_to_message_id") or "",
                "reply_to_message_ids": cached_msg.get("reply_to_message_ids") or [],
                "image_refs": cached_msg.get("image_refs")
                or cached_msg.get("image_urls")
                or [],
                "image_descriptions": cached_msg.get("image_descriptions") or [],
                "image_status": cached_msg.get("image_status") or "",
                "image_items": cached_msg.get("image_items") or [],
                "image_policy_version": cached_msg.get("image_policy_version") or "",
                "trigger_source": source
                or (
                    "keyword"
                    if cached_msg.get("has_trigger_keyword")
                    else "at"
                    if cached_msg.get("is_at_message")
                    else "ai_decision"
                ),
                "probability_filtered": bool(cached_msg.get("probability_filtered")),
                "wait_window_message": bool(cached_msg.get("window_buffered")),
            }
            ok = await ContextManager.sqlite_store.add_message_sync(payload)
            if ok:
                logger.info(
                    "[GCP上下文存储] 用户消息已落盘 chat_id=%s source=%s",
                    chat_id,
                    source or payload["trigger_source"],
                )
            return ok
        except Exception as e:
            logger.warning("[GCP上下文存储] 保存缓存用户消息失败: %s", e, exc_info=True)
            return False

    @staticmethod
    async def save_bot_message(
        event: AstrMessageEvent, bot_message_text: str, context: "Context" = None
    ) -> bool:
        """
        Save assistant replies into group_chat_plus SQLite storage.

        AstrBot official history/conversation is not used as the prompt source.
        """
        try:
            from .message_cleaner import MessageCleaner

            cleaned_message = (
                MessageCleaner.clean_message(bot_message_text) or bot_message_text
            )
            platform_id, chat_id, chat_type, _ = ContextManager._get_chat_ids(event)
            if not chat_id:
                logger.warning("Missing chat_id, skip saving assistant message")
                return False
            if not ContextManager.sqlite_store:
                logger.warning("[ContextManager] SQLite store is not initialized")
                return False

            bot_nickname = "AI"
            try:
                if hasattr(event, "get_self_name") and callable(event.get_self_name):
                    bot_nickname = event.get_self_name() or "AI"
            except Exception:
                pass

            payload = {
                "message_id": f"bot_{time.time_ns()}",
                "platform_name": event.get_platform_name(),
                "platform_id": platform_id,
                "chat_id": chat_id,
                "chat_key": ContextManager._session_key(platform_id, chat_id),
                "chat_type": chat_type,
                "role": "assistant",
                "sender_id": event.get_self_id(),
                "sender_name": bot_nickname,
                "timestamp": time.time(),
                "content": cleaned_message,
            }
            ok = await ContextManager.sqlite_store.add_message_sync(payload)
            if ok:
                logger.info("[GCP context] assistant message saved chat_id=%s", chat_id)
            return ok

        except Exception as e:
            logger.error(f"Failed to save assistant message: {e}", exc_info=True)
            return False

    @staticmethod
    async def save_bot_message_by_params(
        platform_name: str,
        is_private: bool,
        chat_id: str,
        bot_message_text: str,
        self_id: str,
        context: "Context" = None,
        platform_id: str = None,
    ) -> bool:
        """
        保存AI回复（无需event对象）
        复用 save_bot_message 的核心逻辑，保持一致性

        Args:
            platform_name: 平台名称
            is_private: 是否私聊
            chat_id: 聊天ID
            bot_message_text: AI回复文本
            self_id: 机器人ID
            context: Context对象（兼容参数，不写官方存储）
            platform_id: 平台ID

        Returns:
            是否成功
        """
        try:
            from .message_cleaner import MessageCleaner

            cleaned_message = (
                MessageCleaner.clean_message(bot_message_text) or bot_message_text
            )
            if not chat_id:
                logger.warning("无法获取聊天ID,跳过消息保存")
                return False
            if not ContextManager.sqlite_store:
                logger.warning("[上下文管理器] SQLite存储未初始化，AI消息未保存")
                return False

            real_platform_id = str(platform_id or platform_name or "")
            chat_type = "private" if is_private else "group"
            payload = {
                "message_id": f"bot_{time.time_ns()}",
                "platform_name": platform_name,
                "platform_id": real_platform_id,
                "chat_id": str(chat_id),
                "chat_key": ContextManager._session_key(real_platform_id, str(chat_id)),
                "chat_type": chat_type,
                "role": "assistant",
                "sender_id": self_id,
                "sender_name": "AI",
                "timestamp": time.time(),
                "content": cleaned_message,
            }
            ok = await ContextManager.sqlite_store.add_message_sync(payload)
            if ok:
                logger.info("[GCP上下文存储] AI回复已落盘 chat_id=%s", chat_id)
            return ok

        except Exception as e:
            logger.error(f"保存AI消息失败: {e}", exc_info=True)
            return False

    @staticmethod
    async def save_to_official_conversation(
        event: AstrMessageEvent, user_message: str, bot_message: str, context: "Context"
    ) -> bool:
        """
        兼容旧调用名：只保存到插件自有 SQLite。

        group_chat_plus 不再写入 AstrBot 官方 conversation_manager，避免官方
        一问一答式历史重新进入上下文主链路。
        """
        return await ContextManager.save_to_official_conversation_with_cache(
            event,
            [],
            user_message,
            bot_message,
            context,
        )

    @staticmethod
    async def _try_official_save(
        cm, unified_msg_origin: str, conversation_id: str, history_list: list
    ) -> bool:
        """
        已停用的兼容桩。

        插件现在只维护自有 SQLite 上下文，不再主动写 AstrBot 官方对话。
        """
        logger.info("[GCP上下文存储] 官方 conversation_manager 写入已停用")
        return False

    @staticmethod
    async def save_to_official_conversation_with_cache(
        event: AstrMessageEvent,
        cached_messages: list,
        user_message: str,
        bot_message: str,
        context: "Context",
    ) -> bool:
        """
        兼容旧调用名：将当前用户消息/AI回复保存到插件自有 SQLite。

        不再写入 AstrBot 官方 conversation_manager，避免官方一问一答历史
        重新进入群聊上下文主链路。

        Args:
            event: 消息事件
            cached_messages: 已废弃兼容参数，内部忽略
            user_message: 当前用户消息（原始，不带元数据）
            bot_message: AI回复
            context: Context对象

        Returns:
            是否成功
        """
        try:
            from .message_cleaner import MessageCleaner

            platform_id, chat_id, chat_type, _ = ContextManager._get_chat_ids(event)
            if not chat_id or not ContextManager.sqlite_store:
                return False

            saved = 0

            if user_message:
                user_message = MessageCleaner.clean_message(user_message) or user_message
                msg_id = ""
                try:
                    msg_id = str(getattr(event.message_obj, "message_id", "") or "")
                except Exception:
                    pass
                image_meta = {}
                try:
                    image_meta = event.get_extra("gcp_image_meta", {}) or {}
                except Exception:
                    image_meta = {}
                await ContextManager.sqlite_store.add_message_sync(
                    {
                        "message_id": msg_id or f"user_{time.time_ns()}",
                        "platform_name": event.get_platform_name(),
                        "platform_id": platform_id,
                        "chat_id": chat_id,
                        "chat_key": ContextManager._session_key(platform_id, chat_id),
                        "chat_type": chat_type,
                        "role": "user",
                        "sender_id": event.get_sender_id(),
                        "sender_name": event.get_sender_name() or "未知用户",
                        "timestamp": time.time(),
                        "content": user_message,
                        "image_refs": image_meta.get("image_refs") or [],
                        "image_descriptions": image_meta.get("image_descriptions") or [],
                        "image_status": image_meta.get("image_status") or "",
                        "image_items": image_meta.get("image_items") or [],
                        "image_policy_version": image_meta.get("policy_version") or "",
                    }
                )
                saved += 1

            if bot_message:
                await ContextManager.save_bot_message(event, bot_message, context=None)
                saved += 1

            logger.info(
                "[GCP上下文存储] 兼容保存完成 chat_id=%s, 写入=%d",
                chat_id,
                saved,
            )
            return True

        except Exception as e:
            logger.error(
                f"[GCP上下文存储] 兼容保存失败: {e}", exc_info=True
            )
            return False

"""Prompt helpers for image gate / structured vision output."""

from __future__ import annotations

import re
from typing import List

from astrbot.api.all import *
from astrbot.api.message_components import At, Face, Reply


DEFAULT_IMAGE_TO_TEXT_SYSTEM_PROMPT = (
    "你是图片结构化解析器，只负责把输入图片转换为严格 JSON。\n"
    "只能输出一个 JSON 对象，不要输出 Markdown、代码块、解释、寒暄或任何额外文本。\n"
    'JSON 字段只能包含: {"description":"中文图片描述","importance":0.0}\n'
    "description 必须是中文字符串，需要说明图片的表面内容、可能的梗、隐含含义和群聊理解所需信息。\n"
    "importance 必须是 0 到 1 的数字，表示这张图片对后续群聊上下文的必要程度："
    "0 表示几乎没有保留价值，1 表示强烈需要保留。\n"
    "判定原则：importance 评的是“是否值得进入后续群聊上下文”，"
    "不是“有多离谱、有多好笑、有多刺激”。\n"
    "如果图片属于多图连发、刷屏、同质截图、表情包合集、重复梗图、低新颖度转发，importance 应明显降低。\n"
    "如果局部上下文出现 [上文图片]、[上文连续图片×N] 或 [近期群内图片较多，前文图片已压缩]，"
    "只把它当作刷图背景信号，不要推断那些图片的具体内容。"
)


def build_structured_system_prompt(system_prompt: str = "") -> str:
    custom_prompt = str(system_prompt or "").strip()
    if not custom_prompt:
        return DEFAULT_IMAGE_TO_TEXT_SYSTEM_PROMPT
    return f"{DEFAULT_IMAGE_TO_TEXT_SYSTEM_PROMPT}\n\n补充要求：\n{custom_prompt}"


def build_structured_prompt(prompt: str, context_hint: str = "") -> str:
    base_prompt = str(prompt or "").strip() or "请用中文详细描述这幅图片。"
    parts = [
        base_prompt,
        "请根据当前图片和局部上下文输出上面的 JSON。",
    ]
    hint = str(context_hint or "").strip()
    if hint:
        parts.append(f"局部上下文：\n{hint}")
        parts.append("局部上下文只用于判断这张图对群聊是否值得保留，不要把刷屏气氛当成高重要性。")
    return "\n\n".join(parts)


def compact_context_text(text: str, max_chars: int = 300) -> str:
    compacted = re.sub(r"\s+", " ", str(text or "")).strip()
    if len(compacted) <= max_chars:
        return compacted
    return f"{compacted[:max_chars]}..."


def _format_special_component(component: BaseMessageComponent) -> str:
    if isinstance(component, Face):
        return f"[表情:{component.id}]"
    if isinstance(component, At):
        return f"[At:{component.qq}]"
    if isinstance(component, Reply):
        try:
            message_content = getattr(component, "message_str", None) or getattr(
                component, "message", None
            )
            sender_nickname = getattr(component, "sender_nickname", None) or getattr(
                component, "sender_name", None
            )
            if not sender_nickname and hasattr(component, "sender"):
                sender_nickname = getattr(component.sender, "nickname", None)
            sender_id = getattr(component, "sender_id", None)
            if message_content:
                if sender_nickname and sender_id:
                    return f"[引用 {sender_nickname}(ID:{sender_id}): {message_content}]"
                if sender_id:
                    return f"[引用 用户(ID:{sender_id}): {message_content}]"
                if sender_nickname:
                    return f"[引用 {sender_nickname}: {message_content}]"
                return f"[引用消息: {message_content}]"
            return "[引用消息]"
        except Exception:
            return "[引用消息]"
    return ""


def _extract_text_only(message_chain: List[BaseMessageComponent]) -> str:
    text_parts = []
    for component in message_chain:
        if isinstance(component, Plain):
            text_parts.append(component.text)
        elif isinstance(component, Image):
            continue
        else:
            formatted = _format_special_component(component)
            if formatted:
                text_parts.append(formatted)
    return "".join(text_parts).strip()


def build_image_context_hint(
    message_chain: List[BaseMessageComponent],
    image_index: int,
    image_count: int,
    burst_factor: float = 1.0,
) -> str:
    notes: list[str] = []
    text_context = compact_context_text(_extract_text_only(message_chain))
    if text_context:
        notes.append(f"当前消息文字：{text_context}")

    if image_index == 1:
        notes.append("[上文图片]")
    elif image_index > 1:
        notes.append(f"[上文连续图片×{image_index}]")

    if image_count > 1:
        notes.append(f"当前消息共 {image_count} 张图片，本图是第 {image_index + 1} 张。")

    if burst_factor < 1.0:
        notes.append("[近期群内图片较多，前文图片已压缩]")

    return "\n".join(notes)


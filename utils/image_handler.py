"""Image handling and image importance gating."""

from __future__ import annotations

import asyncio
import json
import re
import time
from typing import List, Optional, Tuple

from astrbot.api.all import *
from astrbot.api.message_components import At, Face, Reply

from .image_description_cache import ImageDescriptionCache
from .image_gate_prompt import (
    build_image_context_hint as _build_image_context_hint_impl,
    build_structured_prompt as _build_structured_prompt_impl,
    build_structured_system_prompt as _build_structured_system_prompt_impl,
    compact_context_text as _compact_context_text_impl,
)
from .image_importance_policy import ImageImportancePolicy, POLICY_VERSION
from .image_spam_gate import ImageSpamDecision, ImageSpamGate


DEBUG_MODE: bool = False

DEFAULT_IMAGE_TO_TEXT_SYSTEM_PROMPT = (
    "你是图片结构化解析器，只负责把输入图片转换为严格 JSON。\n"
    "只能输出一个 JSON 对象，不要输出 Markdown、代码块、解释、寒暄或任何额外文本。\n"
    'JSON 字段只能包含: {"description":"中文图片描述","importance":0.0}\n'
    "description 必须是中文字符串，需要说明图片的表面内容、可能的梗/隐含含义和群聊理解所需信息。\n"
    "importance 必须是 0 到 1 的数字，表示这张图片对后续群聊上下文的必要程度："
    "0 表示几乎没有保留价值，1 表示强烈需要保留。\n"
    "只根据当前图片和提供的局部上下文评分；如果局部上下文出现 [上文图片]、[上文连续图片×N] "
    "或 [近期群内图片较多，前文图片已压缩]，只把它当作刷图背景信号，不要推断那些图片的具体内容。"
)


class ImageHandler:
    """Handle image extraction, vision calls, and prompt gating."""

    @staticmethod
    async def process_message_images(
        event: AstrMessageEvent,
        context: Context,
        enable_image_processing: bool,
        image_to_text_scope: str,
        image_to_text_provider_id: str,
        image_to_text_prompt: str,
        is_at_message: bool,
        has_trigger_keyword: bool,
        timeout: int = 60,
        image_description_cache: Optional[ImageDescriptionCache] = None,
        max_images_per_message: int = 10,
        image_importance_policy: Optional[ImageImportancePolicy] = None,
        image_spam_gate: Optional[ImageSpamGate] = None,
        image_to_text_system_prompt: str = "",
        skip_active_image_understanding: bool = False,
    ) -> Tuple[bool, str, List[str], bool, List[dict]]:
        try:
            if not hasattr(event, "message_obj") or not hasattr(
                event.message_obj, "message"
            ):
                return True, event.get_message_outline(), [], False, []

            message_chain = event.message_obj.message
            has_image, has_text, image_components = ImageHandler._analyze_message(
                message_chain, max_images_per_message
            )
            has_reply_component = any(isinstance(component, Reply) for component in message_chain)

            if not has_image:
                text_content = ImageHandler._extract_text_only(message_chain)
                if not text_content:
                    text_content = event.get_message_outline()
                return True, text_content, [], False, []

            if DEBUG_MODE:
                logger.info(
                    "检测到消息包含 %d 张图片, 文本? %s",
                    len(image_components),
                    has_text,
                )

            if not enable_image_processing:
                if not has_text:
                    return False, "", [], False, []
                return True, ImageHandler._extract_text_only(message_chain), [], False, []

            chat_key = ImageHandler._event_chat_key(event)
            sender_id = ImageHandler._event_sender_id(event)

            if skip_active_image_understanding:
                image_statuses = await ImageHandler._build_pending_image_statuses(
                    image_components,
                    "active_image_blacklist",
                )
                return (
                    True,
                    ImageHandler._build_placeholder_message_text(message_chain),
                    [],
                    False,
                    image_statuses,
                )

            burst_factor = 1.0
            if image_importance_policy:
                burst_factor = image_importance_policy.register_image_batch(
                    chat_key=chat_key,
                    image_count=len(image_components),
                    timestamp=time.time(),
                )
            batch_factor = (
                image_importance_policy.batch_factor(len(image_components))
                if image_importance_policy
                else 1.0
            )
            spam_decision = ImageHandler._evaluate_spam_gate(
                image_spam_gate,
                chat_key=chat_key,
                sender_id=sender_id,
                image_count=len(image_components),
                batch_factor=batch_factor,
                burst_factor=burst_factor,
                quoted=has_reply_component,
            )
            if spam_decision and spam_decision.skip:
                image_statuses = []
                for idx, img_component in enumerate(image_components):
                    try:
                        image_ref = await img_component.convert_to_file_path()
                    except Exception:
                        image_ref = ""
                    image_statuses.append(
                        {
                            "index": idx,
                            "image_ref": image_ref or "",
                            "status": "skipped_spam_batch",
                            "description": "",
                            "failure_reason": spam_decision.reason,
                            "importance": 0.0,
                            "effective_importance": 0.0,
                            "time_factor": 1.0,
                            "burst_factor": burst_factor,
                            "batch_factor": batch_factor,
                            "threshold": 0.0,
                            "keep": False,
                            "gate_reason": spam_decision.reason,
                            "policy_version": "image_spam_gate_v1",
                        }
                    )
                return True, ImageHandler._build_placeholder_message_text(message_chain), [], False, image_statuses

            # image_to_text_scope is kept for compatibility only.
            if not image_to_text_provider_id:
                image_urls = await ImageHandler._extract_image_urls(image_components)
                image_statuses = [
                    {
                        "index": idx,
                        "image_ref": url,
                        "status": "multimodal_url",
                        "description": "",
                        "failure_reason": "",
                        "importance": 1.0,
                        "effective_importance": 1.0,
                        "keep": True,
                        "gate_reason": "multimodal_url",
                        "policy_version": POLICY_VERSION,
                    }
                    for idx, url in enumerate(image_urls)
                ]
                text_content = ImageHandler._extract_text_only(message_chain)
                return True, text_content, image_urls, True, image_statuses

            processed_message, image_statuses = await ImageHandler._convert_images_to_text(
                message_chain,
                context,
                image_to_text_provider_id,
                image_to_text_prompt,
                image_components,
                timeout,
                image_description_cache,
                image_importance_policy,
                chat_key,
                sender_id,
                image_spam_gate,
                image_to_text_system_prompt,
            )

            if processed_message is None:
                if not has_text:
                    fallback_parts = []
                    for comp in message_chain:
                        if isinstance(comp, Image):
                            fallback_parts.append("[图片(识别失败)]")
                        else:
                            fmt = ImageHandler._format_special_component(comp)
                            if fmt:
                                fallback_parts.append(fmt)
                    fallback_text = "".join(fallback_parts).strip() or "[图片(识别失败)]"
                    return True, fallback_text, [], False, image_statuses
                return True, ImageHandler._extract_text_only(message_chain), [], False, image_statuses

            return True, processed_message, [], any(
                bool(item.get("keep")) for item in image_statuses or []
            ), image_statuses

        except Exception as exc:
            logger.error("处理消息图片时发生错误: %s", exc)
            return True, event.get_message_outline(), [], False, []

    @staticmethod
    def _analyze_message(
        message_chain: List[BaseMessageComponent],
        max_images: int = 10,
    ) -> Tuple[bool, bool, List[Image]]:
        has_image = False
        has_text = False
        image_components: List[Image] = []

        for component in message_chain:
            if isinstance(component, Image):
                has_image = True
                image_components.append(component)
            elif isinstance(component, Plain):
                if component.text and component.text.strip():
                    has_text = True
            elif isinstance(component, Reply):
                has_text = True

        if len(image_components) > max_images:
            logger.warning(
                "[图片处理] 单条消息包含 %d 张图片，超过上限 %d，仅处理前 %d 张",
                len(image_components),
                max_images,
                max_images,
            )
            image_components = image_components[:max_images]

        return has_image, has_text, image_components

    @staticmethod
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
                sender_nickname = getattr(
                    component, "sender_nickname", None
                ) or getattr(component, "sender_name", None)
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

    @staticmethod
    def _extract_text_only(message_chain: List[BaseMessageComponent]) -> str:
        text_parts = []
        for component in message_chain:
            if isinstance(component, Plain):
                text_parts.append(component.text)
            elif isinstance(component, Image):
                continue
            else:
                formatted = ImageHandler._format_special_component(component)
                if formatted:
                    text_parts.append(formatted)
        return "".join(text_parts).strip()

    @staticmethod
    async def _extract_image_urls(image_components: List[Image]) -> List[str]:
        image_urls = []
        for idx, img_component in enumerate(image_components):
            try:
                image_path = await img_component.convert_to_file_path()
                if image_path:
                    image_urls.append(image_path)
                else:
                    logger.warning("无法提取图片 %d 的路径", idx)
            except Exception as exc:
                logger.error("提取图片 %d 路径失败: %s", idx, exc)
        return image_urls

    @staticmethod
    def _event_chat_key(event: AstrMessageEvent) -> str:
        try:
            platform_id = str(event.get_platform_id() or event.get_platform_name() or "")
        except Exception:
            platform_id = ""
        try:
            chat_id = (
                event.get_group_id()
                if not event.is_private_chat()
                else event.get_sender_id()
            )
        except Exception:
            chat_id = ""
        return f"{platform_id}:{chat_id or 'unknown'}"

    @staticmethod
    def _event_sender_id(event: AstrMessageEvent) -> str:
        try:
            return str(event.get_sender_id() or "")
        except Exception:
            return ""

    @staticmethod
    def _evaluate_spam_gate(
        image_spam_gate: Optional[ImageSpamGate],
        *,
        chat_key: str,
        sender_id: str,
        image_count: int,
        batch_factor: float,
        burst_factor: float,
        quoted: bool,
    ) -> ImageSpamDecision | None:
        if not image_spam_gate:
            return None
        try:
            return image_spam_gate.evaluate(
                chat_key=chat_key,
                sender_id=sender_id,
                image_count=image_count,
                batch_factor=batch_factor,
                burst_factor=burst_factor,
                quoted=quoted,
            )
        except Exception as exc:
            logger.warning("[GCP图片刷图门] evaluate failed: %s", exc)
            return None

    @staticmethod
    def _build_structured_system_prompt(system_prompt: str = "") -> str:
        return _build_structured_system_prompt_impl(system_prompt)

    @staticmethod
    def _build_structured_prompt(prompt: str, context_hint: str = "") -> str:
        return _build_structured_prompt_impl(prompt, context_hint)

    @staticmethod
    def _compact_context_text(text: str, max_chars: int = 300) -> str:
        return _compact_context_text_impl(text, max_chars)

    @staticmethod
    def _build_image_context_hint(
        message_chain: List[BaseMessageComponent],
        image_index: int,
        image_count: int,
        burst_factor: float = 1.0,
    ) -> str:
        return _build_image_context_hint_impl(
            message_chain,
            image_index,
            image_count,
            burst_factor,
        )

    @staticmethod
    def _parse_structured_image_response(raw_text: str) -> tuple[str, float, bool, str]:
        raw = str(raw_text or "").strip()
        if not raw:
            return "", 0.0, False, "empty_response"

        candidates = [raw]
        fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.S)
        if fence_match:
            candidates.insert(0, fence_match.group(1))
        object_match = re.search(r"\{.*\}", raw, re.S)
        if object_match:
            candidates.append(object_match.group(0))

        for candidate in candidates:
            try:
                data = json.loads(candidate)
            except Exception:
                continue
            if not isinstance(data, dict):
                continue

            extra_keys = set(data.keys()) - {"description", "importance"}
            if extra_keys:
                return "", 0.0, False, "unexpected_fields"

            description = str(data.get("description") or "").strip()
            if not description:
                return "", 0.0, False, "missing_description"

            try:
                importance = float(data.get("importance"))
            except Exception:
                return description, 0.0, False, "invalid_importance"

            if importance < 0.0 or importance > 1.0:
                return (
                    description,
                    max(0.0, min(1.0, importance)),
                    False,
                    "importance_out_of_range",
                )

            return description, importance, True, ""

        return "", 0.0, False, "json_parse_failed"

    @staticmethod
    def _placeholder_image_status(
        idx: int,
        image_ref: str,
        status: str,
        failure_reason: str,
    ) -> dict:
        return {
            "index": idx,
            "image_ref": image_ref or "",
            "status": status,
            "description": "",
            "failure_reason": failure_reason,
            "importance": 0.0,
            "effective_importance": 0.0,
            "keep": False,
            "gate_reason": failure_reason,
            "policy_version": POLICY_VERSION,
        }

    @staticmethod
    async def _build_pending_image_statuses(
        image_components: List[Image],
        failure_reason: str,
    ) -> list[dict]:
        image_statuses: list[dict] = []
        for idx, img_component in enumerate(image_components):
            try:
                image_ref = await img_component.convert_to_file_path()
            except Exception:
                image_ref = ""
            image_statuses.append(
                ImageHandler._placeholder_image_status(
                    idx,
                    image_ref,
                    "pending_retry",
                    failure_reason,
                )
            )
        return image_statuses

    @staticmethod
    def _build_placeholder_message_text(message_chain: List[BaseMessageComponent]) -> str:
        parts: list[str] = []
        for component in message_chain:
            if isinstance(component, Plain):
                parts.append(component.text)
            elif isinstance(component, Image):
                parts.append("[图片]")
            else:
                formatted = ImageHandler._format_special_component(component)
                if formatted:
                    parts.append(formatted)
        return "".join(parts).strip()

    @staticmethod
    async def _convert_images_to_text(
        message_chain: List[BaseMessageComponent],
        context: Context,
        provider_id: str,
        prompt: str,
        image_components: List[Image],
        timeout: int = 60,
        image_description_cache: Optional[ImageDescriptionCache] = None,
        image_importance_policy: Optional[ImageImportancePolicy] = None,
        chat_key: str = "",
        sender_id: str = "",
        image_spam_gate: Optional[ImageSpamGate] = None,
        image_to_text_system_prompt: str = "",
    ) -> Tuple[Optional[str], List[dict]]:
        try:
            provider = context.get_provider_by_id(provider_id)
            if not provider:
                logger.error("无法找到提供商 %s", provider_id)
                return None, [
                    ImageHandler._placeholder_image_status(
                        idx, "", "pending_retry", f"provider_not_found:{provider_id}"
                    )
                    for idx, _ in enumerate(image_components)
                ]

            image_chain_to_idx: dict[int, int] = {}
            img_count = 0
            for chain_idx, component in enumerate(message_chain):
                if isinstance(component, Image):
                    image_chain_to_idx[chain_idx] = img_count
                    img_count += 1

            burst_factor = 1.0
            if image_importance_policy:
                burst_factor = image_importance_policy.register_image_batch(
                    chat_key=chat_key,
                    image_count=len(image_components),
                    timestamp=time.time(),
                )
            batch_factor = (
                image_importance_policy.batch_factor(len(image_components))
                if image_importance_policy
                else 1.0
            )
            spam_decision = ImageHandler._evaluate_spam_gate(
                image_spam_gate,
                chat_key=chat_key,
                sender_id=sender_id,
                image_count=len(image_components),
                batch_factor=batch_factor,
                burst_factor=burst_factor,
                quoted=any(isinstance(component, Reply) for component in message_chain),
            )

            image_descriptions: dict[int, str] = {}
            image_statuses: list[dict] = []
            structured_system_prompt = ImageHandler._build_structured_system_prompt(
                image_to_text_system_prompt
            )

            if spam_decision and spam_decision.skip:
                placeholder_text = ImageHandler._build_placeholder_message_text(
                    message_chain
                )
                for idx, img_component in enumerate(image_components):
                    try:
                        image_path = await img_component.convert_to_file_path()
                    except Exception:
                        image_path = ""
                    image_statuses.append(
                        {
                            "index": idx,
                            "image_ref": image_path or "",
                            "status": "skipped_spam_batch",
                            "description": "",
                            "failure_reason": spam_decision.reason,
                            "importance": 0.0,
                            "effective_importance": 0.0,
                            "time_factor": 1.0,
                            "burst_factor": burst_factor,
                            "batch_factor": batch_factor,
                            "threshold": 0.0,
                            "keep": False,
                            "gate_reason": spam_decision.reason,
                            "policy_version": "image_spam_gate_v1",
                        }
                    )
                return placeholder_text, image_statuses

            for idx, img_component in enumerate(image_components):
                image_path = ""
                try:
                    image_path = await img_component.convert_to_file_path()
                    if not image_path:
                        image_statuses.append(
                            ImageHandler._placeholder_image_status(
                                idx, "", "pending_retry", "empty_image_path"
                            )
                        )
                        continue

                    if DEBUG_MODE:
                        logger.info("正在转换图片 %d: %s", idx, image_path)

                    if image_description_cache and image_description_cache.enabled:
                        cached_desc = image_description_cache.lookup(image_path)
                        if cached_desc:
                            gate = (
                                image_importance_policy.evaluate(
                                    model_importance=0.5,
                                    burst_factor=burst_factor,
                                    batch_factor=batch_factor,
                                ).to_dict()
                                if image_importance_policy
                                else {
                                    "keep": True,
                                    "importance": 0.5,
                                    "effective_importance": 0.5,
                                    "time_factor": 1.0,
                                    "burst_factor": burst_factor,
                                    "batch_factor": batch_factor,
                                    "threshold": 0.0,
                                    "gate_reason": "gate_disabled",
                                    "policy_version": POLICY_VERSION,
                                }
                            )
                            if gate.get("keep"):
                                image_descriptions[idx] = cached_desc
                            image_statuses.append(
                                {
                                    "index": idx,
                                    "image_ref": image_path,
                                    "status": "success",
                                    "description": cached_desc,
                                    "failure_reason": "",
                                    "cache_hit": True,
                                    **gate,
                                }
                            )
                            continue

                    async def call_vision_ai():
                        context_hint = ImageHandler._build_image_context_hint(
                            message_chain,
                            idx,
                            len(image_components),
                            burst_factor,
                        )
                        response = await provider.text_chat(
                            prompt=ImageHandler._build_structured_prompt(
                                prompt, context_hint
                            ),
                            contexts=[],
                            image_urls=[image_path],
                            func_tool=None,
                            system_prompt=structured_system_prompt,
                        )
                        return response.completion_text

                    raw_description = await asyncio.wait_for(
                        call_vision_ai(), timeout=timeout
                    )
                    description, importance, parse_ok, parse_reason = (
                        ImageHandler._parse_structured_image_response(raw_description)
                    )
                    gate = (
                        image_importance_policy.evaluate(
                            model_importance=importance,
                            burst_factor=burst_factor,
                            batch_factor=batch_factor,
                        ).to_dict()
                        if image_importance_policy
                        else {
                            "keep": True,
                            "importance": importance,
                            "effective_importance": importance,
                            "time_factor": 1.0,
                            "burst_factor": burst_factor,
                            "batch_factor": batch_factor,
                            "threshold": 0.0,
                            "gate_reason": "gate_disabled",
                            "policy_version": POLICY_VERSION,
                        }
                    )
                    if not parse_ok:
                        gate = {
                            **gate,
                            "keep": False,
                            "gate_reason": parse_reason,
                        }

                    if gate.get("keep") and description:
                        image_descriptions[idx] = description

                    status = "success" if parse_ok else "failed_final"
                    image_statuses.append(
                        {
                            "index": idx,
                            "image_ref": image_path,
                            "status": status,
                            "description": description if parse_ok else "",
                            "failure_reason": "" if parse_ok else parse_reason,
                            "importance": importance,
                            "effective_importance": gate.get("effective_importance", 0.0),
                            "time_factor": gate.get("time_factor", 1.0),
                            "burst_factor": gate.get("burst_factor", 1.0),
                            "batch_factor": gate.get("batch_factor", 1.0),
                            "threshold": gate.get("threshold", 0.0),
                            "keep": bool(gate.get("keep")),
                            "gate_reason": str(gate.get("gate_reason") or ""),
                            "policy_version": gate.get("policy_version")
                            or POLICY_VERSION,
                        }
                    )

                    if (
                        parse_ok
                        and description
                        and image_description_cache
                        and image_description_cache.enabled
                    ):
                        if not image_description_cache.lookup(image_path):
                            image_description_cache.save(image_path, description)

                except asyncio.TimeoutError:
                    image_statuses.append(
                        ImageHandler._placeholder_image_status(
                            idx,
                            image_path,
                            "pending_retry",
                            f"timeout:{timeout}s",
                        )
                    )
                    continue
                except Exception as exc:
                    logger.error("转换图片 %d 失败: %s", idx, exc)
                    image_statuses.append(
                        ImageHandler._placeholder_image_status(
                            idx,
                            image_path,
                            "pending_retry",
                            str(exc),
                        )
                    )
                    continue

            if not any(item.get("status") in {"success", "failed_final"} for item in image_statuses):
                return None, image_statuses

            result_parts = []
            for chain_idx, component in enumerate(message_chain):
                if isinstance(component, Plain):
                    result_parts.append(component.text)
                elif isinstance(component, Image):
                    if chain_idx in image_chain_to_idx:
                        img_idx = image_chain_to_idx[chain_idx]
                        if img_idx in image_descriptions:
                            result_parts.append(f"[图片内容: {image_descriptions[img_idx]}]")
                        else:
                            result_parts.append("[图片]")
                    else:
                        result_parts.append("[图片]")
                else:
                    formatted = ImageHandler._format_special_component(component)
                    if formatted:
                        result_parts.append(formatted)

            return "".join(result_parts), image_statuses

        except Exception as exc:
            logger.error("图片转文本过程发生错误: %s", exc)
            return None, []

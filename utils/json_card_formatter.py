"""
JSON 卡片消息格式化工具。

用于从 QQ 小程序/分享卡片类 JSON 消息中提取可读标题与原始链接，
尤其是 OneBot json segment 中常见的 meta.detail_1.qqdocurl。
"""

import html
import json
import re
from typing import Any


def format_json_card_message(payload: Any, fallback: str = "[JSON消息]") -> str:
    """
    将 AstrBot Json 组件或 OneBot json segment 的 data 格式化为可落库文本。

    Args:
        payload: 可能是 dict、JSON 字符串、{"data": "{...}"} 包装结构等。
        fallback: 无法解析出有效信息时返回的占位文本。

    Returns:
        例如："[JSON卡片: 哔哩哔哩 - 标题](原始消息：https://b23.tv/xxx)"
    """
    try:
        card_data = normalize_json_payload(payload)
        if not isinstance(card_data, dict):
            return fallback

        label = _extract_card_label(card_data)
        url = _extract_preferred_url(card_data)

        if label and url:
            return f"[JSON卡片: {label}](原始消息：{url})"
        if url:
            return f"[JSON卡片](原始消息：{url})"
        if label:
            return f"[JSON卡片: {label}]"
        return fallback
    except Exception:
        return fallback


def normalize_json_payload(payload: Any) -> Any:
    """兼容 AstrBot Json.data、OneBot segment data 以及字符串 JSON。"""
    current = payload
    for _ in range(8):
        if isinstance(current, str):
            parsed = _safe_json_loads(current)
            if parsed is None:
                return current
            current = parsed
            continue

        if isinstance(current, dict):
            # OneBot json segment 通常形如：{"data": "{...真实卡片JSON...}"}
            inner = current.get("data")
            if inner is not None and isinstance(inner, (str, dict, list)):
                # 如果当前 dict 本身不像卡片，而内层可能才是真实卡片，则继续向内剥离。
                if not _looks_like_card_payload(current):
                    current = inner
                    continue
            return current

        return current

    return current


def _safe_json_loads(raw: str) -> Any | None:
    text = raw.strip()
    if not text:
        return None

    # CQ/HTML 转义中常见 &#44;、&amp;，这里先还原再解析。
    candidates = [text, html.unescape(text), text.replace("&#44;", ",")]
    seen = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        try:
            return json.loads(candidate)
        except Exception:
            continue
    return None


def _looks_like_card_payload(value: dict) -> bool:
    marker_keys = {
        "app",
        "meta",
        "prompt",
        "config",
        "ver",
        "view",
        "title",
        "desc",
        "url",
        "qqdocurl",
    }
    return any(key in value for key in marker_keys)


def _extract_card_label(card_data: dict) -> str:
    prompt = _clean_text(card_data.get("prompt"))
    top_title = _clean_text(card_data.get("title"))
    top_desc = _clean_text(
        card_data.get("desc") or card_data.get("summary") or card_data.get("text")
    )

    detail = _find_preferred_detail(card_data)
    detail_title = ""
    detail_desc = ""
    if isinstance(detail, dict):
        detail_title = _clean_text(
            detail.get("title")
            or detail.get("source")
            or detail.get("app_name")
            or detail.get("tag")
        )
        detail_desc = _clean_text(
            detail.get("desc")
            or detail.get("summary")
            or detail.get("text")
            or detail.get("content")
        )

    title = detail_title or top_title
    desc = detail_desc or top_desc

    if title and desc and title != desc:
        return _truncate_text(f"{title} - {desc}")
    if title:
        return _truncate_text(title)
    if desc:
        return _truncate_text(desc)
    if prompt:
        return _truncate_text(prompt)
    return ""


def _find_preferred_detail(card_data: dict) -> dict | None:
    meta = card_data.get("meta")
    if not isinstance(meta, dict):
        return None

    for key in ("detail_1", "detail"):
        detail = meta.get(key)
        if isinstance(detail, dict):
            return detail

    for detail in meta.values():
        if isinstance(detail, dict):
            return detail
    return None


def _extract_preferred_url(card_data: dict) -> str:
    candidates: list[tuple[int, str]] = []

    def add(value: Any, priority: int) -> None:
        url = _normalize_url(value)
        if not url:
            return
        score = priority + _url_bonus(url)
        candidates.append((score, url))

    # 明确优先级：QQ/B站分享卡片真实外链通常在 qqdocurl。
    add(_get_nested(card_data, ("meta", "detail_1", "qqdocurl")), 1000)
    add(_get_nested(card_data, ("meta", "detail", "qqdocurl")), 950)
    add(card_data.get("qqdocurl"), 900)

    meta = card_data.get("meta")
    if isinstance(meta, dict):
        for detail in meta.values():
            if isinstance(detail, dict):
                add(detail.get("qqdocurl"), 850)
        add(_get_nested(card_data, ("meta", "detail_1", "url")), 700)
        add(_get_nested(card_data, ("meta", "detail", "url")), 650)
        for detail in meta.values():
            if isinstance(detail, dict):
                add(detail.get("url"), 600)

    for key in (
        "jumpUrl",
        "jumpURL",
        "sourceUrl",
        "source_url",
        "shareUrl",
        "share_url",
        "link",
        "url",
    ):
        add(card_data.get(key), 500)

    # 兜底递归搜索，覆盖不同卡片模板中的同义字段。
    for path, value in _iter_key_values(card_data):
        key = str(path[-1]).lower() if path else ""
        if key == "qqdocurl":
            add(value, 800)
        elif key in {
            "jumpurl",
            "sourceurl",
            "source_url",
            "shareurl",
            "share_url",
            "link",
        }:
            add(value, 450)
        elif key == "url":
            add(value, 350)

    if not candidates:
        return ""

    # 去重后按分数选择最可信链接。
    best_by_url: dict[str, int] = {}
    for score, url in candidates:
        best_by_url[url] = max(best_by_url.get(url, 0), score)

    return max(best_by_url.items(), key=lambda item: item[1])[0]


def _get_nested(value: Any, path: tuple[str, ...]) -> Any:
    current = value
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _iter_key_values(value: Any, path: tuple[Any, ...] = ()):  # noqa: ANN201
    if isinstance(value, dict):
        for key, item in value.items():
            current_path = (*path, key)
            yield current_path, item
            yield from _iter_key_values(item, current_path)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from _iter_key_values(item, (*path, index))


def _normalize_url(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    url = html.unescape(value).strip().replace("\\/", "/")
    if not url:
        return ""

    if url.startswith("//"):
        url = f"https:{url}"
    elif re.match(r"^[A-Za-z0-9.-]+\.[A-Za-z]{2,}(/|$)", url):
        url = f"https://{url}"

    if not re.match(r"^https?://", url, flags=re.IGNORECASE):
        return ""
    return _trim_share_url(url)


def _trim_share_url(url: str) -> str:
    """裁剪分享链接中的非必要追踪参数，优先保留可直接打开的短链。"""
    b23_match = re.match(r"^(https?://b23\.tv/[^/?#\s]+)", url, flags=re.IGNORECASE)
    if b23_match:
        return b23_match.group(1)

    return url


def _url_bonus(url: str) -> int:
    lowered = url.lower()
    bonus = 0
    if "b23.tv" in lowered or "bilibili.com" in lowered:
        bonus += 80
    if "m.q.qq.com" in lowered:
        bonus += 20
    if lowered.startswith("https://"):
        bonus += 5
    return bonus


def _clean_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    text = html.unescape(value).replace("\\/", "/")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _truncate_text(text: str, max_length: int = 120) -> str:
    if len(text) <= max_length:
        return text
    return f"{text[: max_length - 3]}..."
"""Runtime buffer for short group wait-window additions."""

from __future__ import annotations

import copy
from typing import Any, Iterable


class WaitWindowBuffer:
    """Store extra messages collected during the current wait window.

    Messages in this buffer must already be persisted to SQLite. The buffer is
    only used to append those very recent additions to the current prompt.
    """

    def __init__(self, max_messages: int = 3, debug_mode: bool = False) -> None:
        self.max_messages = max(0, int(max_messages or 0))
        self.debug_mode = bool(debug_mode)
        self._items: dict[str, list[dict[str, Any]]] = {}

    def add(self, chat_id: str, message: dict[str, Any] | None) -> None:
        if not chat_id or not isinstance(message, dict) or self.max_messages <= 0:
            return
        key = str(chat_id)
        item = copy.deepcopy(message)
        item["window_buffered"] = True
        item.setdefault("chat_id", key)
        bucket = self._items.setdefault(key, [])
        bucket.append(item)
        bucket.sort(key=self._sort_key)
        if len(bucket) > self.max_messages:
            del bucket[: len(bucket) - self.max_messages]

    def get(self, chat_id: str) -> list[dict[str, Any]]:
        bucket = self._items.get(str(chat_id), [])
        return [copy.deepcopy(item) for item in sorted(bucket, key=self._sort_key)]

    def clear(self, chat_id: str, saved_msg_ids: Iterable[str] | None = None) -> int:
        key = str(chat_id)
        bucket = self._items.get(key)
        if not bucket:
            return 0

        if saved_msg_ids is None:
            removed = len(bucket)
            self._items.pop(key, None)
            return removed

        ids = {str(msg_id) for msg_id in saved_msg_ids if msg_id is not None}
        if not ids:
            return 0
        kept = [item for item in bucket if str(item.get("message_id") or "") not in ids]
        removed = len(bucket) - len(kept)
        if kept:
            self._items[key] = kept
        else:
            self._items.pop(key, None)
        return removed

    def clear_all(self) -> int:
        removed = sum(len(items) for items in self._items.values())
        self._items.clear()
        return removed

    def count(self, chat_id: str) -> int:
        return len(self._items.get(str(chat_id), []))

    def total_count(self) -> int:
        return sum(len(items) for items in self._items.values())

    def chat_ids(self) -> list[str]:
        return list(self._items.keys())

    @staticmethod
    def _sort_key(message: dict[str, Any]) -> tuple[float, str]:
        ts = message.get("message_timestamp") or message.get("timestamp") or 0
        try:
            ts = float(ts)
        except (TypeError, ValueError):
            ts = 0.0
        return ts, str(message.get("message_id") or "")


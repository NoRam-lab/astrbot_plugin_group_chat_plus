"""Small in-memory store for messages currently being processed."""

from __future__ import annotations

import copy
from typing import Any


class RuntimeMessageSnapshotStore:
    """Hold per-message snapshots for concurrent runtime hooks.

    This store is intentionally not a context source. It only helps later
    hooks, such as after-message-sent, recover the exact user message that
    triggered the current processing flow.
    """

    def __init__(self) -> None:
        self._items: dict[str, dict[str, Any]] = {}

    def put(self, message_id: str, snapshot: dict[str, Any] | None) -> None:
        if not message_id or not isinstance(snapshot, dict):
            return
        self._items[str(message_id)] = copy.deepcopy(snapshot)

    def get(self, message_id: str) -> dict[str, Any] | None:
        item = self._items.get(str(message_id))
        return copy.deepcopy(item) if item is not None else None

    def pop(self, message_id: str) -> dict[str, Any] | None:
        item = self._items.pop(str(message_id), None)
        return copy.deepcopy(item) if item is not None else None

    def discard(self, message_id: str) -> None:
        self._items.pop(str(message_id), None)

    def clear(self) -> None:
        self._items.clear()

    def clear_chat(self, chat_id: str) -> int:
        target = str(chat_id)
        keys = [
            key
            for key, item in self._items.items()
            if str(item.get("chat_id") or item.get("group_id") or "") == target
        ]
        for key in keys:
            self._items.pop(key, None)
        return len(keys)

    def __len__(self) -> int:
        return len(self._items)


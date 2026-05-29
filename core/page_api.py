"""AstrBot official plugin Page API for Group Chat Plus."""

from __future__ import annotations

from typing import Any

from astrbot.api import logger
from quart import request

from ..plugin_identity import PLUGIN_LEGACY_NAME, PLUGIN_LOCAL_NAME, PLUGIN_PACKAGE_NAME
from ..utils.context_manager import ContextManager


PAGE_API_PREFIXES = (
    f"/{PLUGIN_PACKAGE_NAME}/page",
    f"/{PLUGIN_LEGACY_NAME}/page",
    f"/{PLUGIN_LOCAL_NAME}/page",
)


class PluginPageApi:
    """GCP short-term context management API for AstrBot plugin Pages."""

    def __init__(self, plugin) -> None:
        self.plugin = plugin

    def register_routes(self) -> None:
        register = self.plugin.context.register_web_api
        routes = [
            ("/stats", self.get_stats, ["GET"], "GCP Page stats"),
            ("/messages", self.list_messages, ["GET"], "GCP Page messages"),
            ("/messages/update", self.update_message, ["POST"], "GCP Page update message"),
            ("/messages/soft-delete", self.soft_delete_message, ["POST"], "GCP Page soft delete message"),
            ("/messages/restore", self.restore_message, ["POST"], "GCP Page restore message"),
            ("/messages/batch-soft-delete", self.batch_soft_delete_messages, ["POST"], "GCP Page batch soft delete messages"),
            ("/maintenance", self.run_maintenance, ["POST"], "GCP Page maintenance"),
        ]
        for prefix in PAGE_API_PREFIXES:
            for suffix, handler, methods, desc in routes:
                register(f"{prefix}{suffix}", handler, methods, desc)

    async def get_stats(self):
        store, error = await self._get_store()
        if error:
            return error

        args = request.args
        platform_id = str(args.get("platform_id", "")).strip()
        chat_id = str(args.get("chat_id", "")).strip()
        try:
            scoped = await store.get_status(platform_id=platform_id, chat_id=chat_id)
            global_status = await store.get_status()
            return self._ok(
                {
                    "scoped": scoped,
                    "global": global_status,
                    "filters": {
                        "platform_id": platform_id,
                        "chat_id": chat_id,
                    },
                }
            )
        except Exception as exc:
            logger.error(f"[GCP PageAPI] 获取统计失败: {exc}", exc_info=True)
            return self._error(str(exc))

    async def list_messages(self):
        store, error = await self._get_store()
        if error:
            return error

        args = request.args
        try:
            page = max(1, int(args.get("page", 1)))
            page_size = min(200, max(1, int(args.get("page_size", 30))))
        except (TypeError, ValueError):
            return self._error("分页参数无效")

        try:
            result = await store.list_messages(
                page=page,
                page_size=page_size,
                db_scope=str(args.get("db", "hot")).strip().lower() or "hot",
                keyword=str(args.get("keyword", "")).strip(),
                platform_id=str(args.get("platform_id", "")).strip(),
                chat_id=str(args.get("chat_id", "")).strip(),
                role=str(args.get("role", "")).strip(),
                image_status=str(args.get("image_status", "")).strip(),
                source=str(args.get("source", "")).strip(),
                include_deleted=self._parse_bool(args.get("include_deleted")),
            )
            return self._ok(result)
        except Exception as exc:
            logger.error(f"[GCP PageAPI] 查询消息失败: {exc}", exc_info=True)
            return self._error(str(exc))

    async def update_message(self):
        store, error = await self._get_store()
        if error:
            return error

        payload = await request.get_json(silent=True) or {}
        selector = self._extract_selector(payload)
        db_scope = self._extract_db_scope(payload, default="all")
        updates: dict[str, Any] = {}
        for field in ("content", "sender_name", "image_status", "image_descriptions"):
            if field in payload:
                updates[field] = payload.get(field)
        if not updates:
            return self._error("没有可更新字段")

        try:
            result = await store.update_message_record(
                selector,
                updates,
                reason=str(payload.get("reason", "")).strip(),
                db_scope=db_scope,
            )
            return self._ok(result)
        except Exception as exc:
            logger.error(f"[GCP PageAPI] 更新消息失败: {exc}", exc_info=True)
            return self._error(str(exc))

    async def soft_delete_message(self):
        payload = await request.get_json(silent=True) or {}
        return await self._soft_delete_selectors([self._extract_selector(payload)], payload)

    async def batch_soft_delete_messages(self):
        payload = await request.get_json(silent=True) or {}
        raw_items = payload.get("messages") or payload.get("selectors") or []
        if not isinstance(raw_items, list) or not raw_items:
            return self._error("需要提供 messages/selectors 列表")
        selectors = [self._extract_selector(item) for item in raw_items if isinstance(item, dict)]
        return await self._soft_delete_selectors(selectors, payload)

    async def restore_message(self):
        store, error = await self._get_store()
        if error:
            return error

        payload = await request.get_json(silent=True) or {}
        try:
            result = await store.restore_messages(
                [self._extract_selector(payload)],
                db_scope=self._extract_db_scope(payload, default="all"),
            )
            return self._ok(result)
        except Exception as exc:
            logger.error(f"[GCP PageAPI] 恢复消息失败: {exc}", exc_info=True)
            return self._error(str(exc))

    async def run_maintenance(self):
        store, error = await self._get_store()
        if error:
            return error
        try:
            await store.run_maintenance()
            status = await store.get_status()
            return self._ok({"message": "maintenance completed", "status": status})
        except Exception as exc:
            logger.error(f"[GCP PageAPI] 手动维护失败: {exc}", exc_info=True)
            return self._error(str(exc))

    async def _soft_delete_selectors(self, selectors: list[dict[str, Any]], payload: dict[str, Any]):
        store, error = await self._get_store()
        if error:
            return error
        if not selectors:
            return self._error("没有有效消息选择器")
        try:
            result = await store.soft_delete_messages(
                selectors,
                reason=str(payload.get("reason", "")).strip(),
                db_scope=self._extract_db_scope(payload, default="all"),
            )
            return self._ok(result)
        except Exception as exc:
            logger.error(f"[GCP PageAPI] 软删除消息失败: {exc}", exc_info=True)
            return self._error(str(exc))

    async def _get_store(self):
        store = ContextManager.sqlite_store
        if not store:
            return None, self._error("GCP SQLite 上下文存储未初始化")
        try:
            if not getattr(store, "_started", False):
                await store.start()
        except Exception as exc:
            logger.error(f"[GCP PageAPI] SQLite 启动失败: {exc}", exc_info=True)
            return None, self._error(str(exc))
        return store, None

    @staticmethod
    def _extract_selector(payload: dict[str, Any]) -> dict[str, Any]:
        selector = payload.get("selector") if isinstance(payload, dict) else None
        if isinstance(selector, dict):
            payload = selector
        selected: dict[str, Any] = {}
        for field in ("id", "platform_id", "chat_id", "message_id", "role"):
            value = payload.get(field)
            if value not in (None, ""):
                selected[field] = value
        return selected

    @staticmethod
    def _extract_db_scope(payload: dict[str, Any], *, default: str = "hot") -> str:
        raw: Any = None
        if isinstance(payload, dict):
            raw = payload.get("db")
            selector = payload.get("selector")
            if raw in (None, "") and isinstance(selector, dict):
                raw = selector.get("db")
        scope = str(raw or default or "hot").strip().lower()
        if scope not in {"hot", "cold", "all"}:
            raise ValueError("db 必须是 hot、cold 或 all")
        return scope

    @staticmethod
    def _parse_bool(value: Any) -> bool:
        if isinstance(value, bool):
            return value
        return str(value or "").strip().lower() in {"1", "true", "yes", "on"}

    @staticmethod
    def _ok(data: Any = None) -> dict[str, Any]:
        return {"success": True, "data": data}

    @staticmethod
    def _error(message: str) -> dict[str, Any]:
        return {"success": False, "error": str(message)}

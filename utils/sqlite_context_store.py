"""
SQLite-backed short-term context storage for Group Chat Plus.

The store owns the plugin's prompt history. It intentionally does not read
AstrBot's official platform/conversation history, because those stores can skip
unanswered group messages and create context gaps.
"""

from __future__ import annotations

import asyncio
import json
import sqlite3
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from astrbot.api import logger


DEBUG_MODE: bool = False


@dataclass
class StoredMessage:
    message_id: str
    platform_name: str
    platform_id: str
    chat_id: str
    chat_key: str
    chat_type: str
    role: str
    sender_id: str
    sender_name: str
    timestamp: float
    content: str
    reply_to_message_id: str
    image_refs: list[str]
    image_descriptions: list[str]
    image_status: str
    trigger_source: str
    probability_filtered: bool
    wait_window_message: bool
    deleted_at: float = 0.0
    deleted_reason: str = ""
    edited_at: float = 0.0
    edit_reason: str = ""
    image_items: list[dict[str, Any]] | None = None
    raw_json: dict[str, Any] | None = None


class SQLiteContextStore:
    """
    Hot/cold SQLite store.

    Hot DB is used for normal prompt construction. Cold DB archives older rows
    and has FTS5 when SQLite supports it.
    """

    def __init__(
        self,
        data_dir: str | Path,
        *,
        hot_retention_days: int = 2,
        cold_retention_days: int = 90,
        cold_max_messages_per_chat: int = 50000,
        flush_batch_size: int = 50,
        flush_interval_seconds: float = 1.0,
        maintenance_interval_hours: float = 24.0,
        maintenance_initial_delay_seconds: float = 300.0,
    ) -> None:
        base = Path(data_dir)
        self.base_dir = base / "sqlite_context"
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.hot_db_path = self.base_dir / "gcp_hot.db"
        self.cold_db_path = self.base_dir / "gcp_cold.db"

        self.hot_retention_days = max(1, int(hot_retention_days or 2))
        self.cold_retention_days = max(self.hot_retention_days, int(cold_retention_days or 90))
        self.cold_max_messages_per_chat = max(1000, int(cold_max_messages_per_chat or 50000))
        self.flush_batch_size = max(1, int(flush_batch_size or 50))
        self.flush_interval_seconds = max(0.1, float(flush_interval_seconds or 1.0))
        # 周期性维护间隔。最小 1 小时，最大 7 天，默认 24 小时。
        try:
            interval = float(maintenance_interval_hours or 24.0)
        except (TypeError, ValueError):
            interval = 24.0
        self.maintenance_interval_seconds = max(3600.0, min(7 * 86400.0, interval * 3600.0))
        # 启动后第一次自动维护的延迟，避免与 initialize() 中的首次维护重叠。
        try:
            initial_delay = float(maintenance_initial_delay_seconds or 0.0)
        except (TypeError, ValueError):
            initial_delay = 300.0
        self.maintenance_initial_delay_seconds = max(0.0, initial_delay)

        self._queue: asyncio.Queue[Any] = asyncio.Queue()
        self._flush_sentinel = object()
        self._flush_lock = asyncio.Lock()
        self._lifecycle_lock = asyncio.Lock()
        self._worker_task: asyncio.Task | None = None
        self._maintenance_task: asyncio.Task | None = None
        self._maintenance_lock = asyncio.Lock()
        self._fts_available: bool = False
        self._started = False
        self._last_error: str = ""
        self._recent_errors: list[dict[str, Any]] = []
        self._last_maintenance_at: float = 0.0
        self._next_maintenance_at: float = 0.0


    async def start(self) -> None:
        if self._started:
            return
        async with self._lifecycle_lock:
            if self._started:
                return
            await asyncio.to_thread(self._initialize_sync)
            self._worker_task = asyncio.create_task(self._writer_loop())
            # 启动周期性归档维护循环（修复：之前只有 initialize 时跑一次，导致热库不会每天归档进冷库）
            self._next_maintenance_at = time.time() + self.maintenance_initial_delay_seconds
            self._maintenance_task = asyncio.create_task(self._maintenance_loop())
            self._started = True
            logger.info(
                "[GCP上下文存储] SQLite已启动 hot=%s cold=%s hot_retention=%sd cold_retention=%sd "
                "maintenance_interval=%.1fh",
                self.hot_db_path,
                self.cold_db_path,
                self.hot_retention_days,
                self.cold_retention_days,
                self.maintenance_interval_seconds / 3600.0,
            )

    async def close(self) -> None:
        async with self._lifecycle_lock:
            if not self._started:
                return
            # 先停维护循环，避免它在写入队列关闭后再触发归档
            if self._maintenance_task and not self._maintenance_task.done():
                self._maintenance_task.cancel()
                try:
                    await self._maintenance_task
                except asyncio.CancelledError:
                    pass
                except Exception as e:
                    self._record_error("maintenance_close", e)
            self._maintenance_task = None
            await self._queue.put(None)
            if self._worker_task:
                try:
                    await self._worker_task
                except Exception as e:
                    self._record_error("writer_close", e)
            self._worker_task = None
            self._started = False


    async def enqueue_message(self, message: dict[str, Any]) -> bool:
        if not self._started:
            await self.start()
        try:
            await self._queue.put(dict(message))
            return True
        except Exception as e:
            self._record_error("enqueue_message", e)
            return False

    async def add_message_sync(self, message: dict[str, Any]) -> bool:
        if not self._started:
            await self.start()
        try:
            await asyncio.to_thread(self._insert_messages_sync, [dict(message)])
            return True
        except Exception as e:
            self._record_error("add_message_sync", e)
            return False

    async def flush(self) -> None:
        if not self._started:
            return
        async with self._flush_lock:
            if not self._started:
                return
            done = asyncio.Event()
            await self._queue.put((self._flush_sentinel, done))
            await done.wait()

    async def get_recent_messages(
        self,
        *,
        platform_id: str,
        chat_id: str,
        limit: int,
        include_cold: bool = False,
    ) -> list[StoredMessage]:
        if not self._started:
            await self.start()
        return await asyncio.to_thread(
            self._get_recent_messages_sync,
            str(platform_id or ""),
            str(chat_id or ""),
            int(limit),
            bool(include_cold),
        )

    async def get_messages_by_ids(
        self,
        *,
        platform_id: str,
        chat_id: str,
        message_ids: list[str],
        include_cold: bool = True,
    ) -> dict[str, StoredMessage]:
        if not self._started:
            await self.start()
        normalized_ids = []
        seen = set()
        for message_id in message_ids or []:
            mid = str(message_id or "").strip()
            if mid and mid not in seen:
                normalized_ids.append(mid)
                seen.add(mid)
        if not normalized_ids:
            return {}
        return await asyncio.to_thread(
            self._get_messages_by_ids_sync,
            str(platform_id or ""),
            str(chat_id or ""),
            normalized_ids,
            bool(include_cold),
        )

    async def get_status(self, *, platform_id: str = "", chat_id: str = "") -> dict[str, Any]:
        if not self._started:
            await self.start()
        status = await asyncio.to_thread(
            self._get_status_sync,
            str(platform_id or ""),
            str(chat_id or ""),
        )
        status["queue_size"] = self._queue.qsize()
        status["last_error"] = self._last_error
        status["recent_errors"] = list(self._recent_errors[-5:])
        status["fts_available"] = self._fts_available
        status["maintenance_interval_hours"] = self.maintenance_interval_seconds / 3600.0
        status["last_maintenance_at"] = float(self._last_maintenance_at or 0.0)
        status["next_maintenance_at"] = float(self._next_maintenance_at or 0.0)
        status["maintenance_running"] = bool(
            self._maintenance_task and not self._maintenance_task.done()
        )
        return status


    async def clear_chat(self, *, platform_id: str, chat_id: str) -> None:
        if not self._started:
            await self.start()
        await self.flush()
        await asyncio.to_thread(
            self._clear_chat_sync,
            str(platform_id or ""),
            str(chat_id or ""),
        )

    async def clear_all(self) -> None:
        if not self._started:
            await self.start()
        await self.flush()
        await asyncio.to_thread(self._clear_all_sync)

    async def run_maintenance(self) -> None:
        if not self._started:
            await self.start()
        async with self._maintenance_lock:
            await self.flush()
            await asyncio.to_thread(self._run_maintenance_sync)

    async def upsert_image_status(self, image: dict[str, Any]) -> None:
        if not self._started:
            await self.start()
        await asyncio.to_thread(self._upsert_image_status_sync, dict(image))

    async def get_pending_images_for_message(
        self,
        *,
        platform_id: str,
        chat_id: str,
        message_id: str,
    ) -> list[dict[str, Any]]:
        if not self._started:
            await self.start()
        return await asyncio.to_thread(
            self._get_pending_images_for_message_sync,
            str(platform_id or ""),
            str(chat_id or ""),
            str(message_id or ""),
        )

    async def mark_image_failed_final(
        self,
        image_key: str,
        reason: str,
    ) -> None:
        if not self._started:
            await self.start()
        await asyncio.to_thread(
            self._update_image_status_sync,
            image_key,
            "failed_final",
            "",
            reason,
            1,
        )

    async def mark_image_succeeded(
        self,
        image_key: str,
        description: str,
    ) -> None:
        if not self._started:
            await self.start()
        await asyncio.to_thread(
            self._update_image_status_sync,
            image_key,
            "success",
            description,
            "",
            0,
        )

    async def update_message_image_result(
        self,
        *,
        platform_id: str,
        chat_id: str,
        message_id: str,
        image_ref: str,
        status: str,
        description: str = "",
        failure_reason: str = "",
    ) -> None:
        if not self._started:
            await self.start()
        await asyncio.to_thread(
            self._update_message_image_result_sync,
            str(platform_id or ""),
            str(chat_id or ""),
            str(message_id or ""),
            str(image_ref or ""),
            str(status or ""),
            str(description or ""),
            str(failure_reason or ""),
        )

    async def list_messages(
        self,
        *,
        page: int = 1,
        page_size: int = 30,
        db_scope: str = "hot",
        keyword: str = "",
        platform_id: str = "",
        chat_id: str = "",
        role: str = "",
        image_status: str = "",
        source: str = "",
        include_deleted: bool = False,
    ) -> dict[str, Any]:
        if not self._started:
            await self.start()
        await self.flush()
        return await asyncio.to_thread(
            self._list_messages_sync,
            int(page or 1),
            int(page_size or 30),
            str(db_scope or "hot"),
            str(keyword or ""),
            str(platform_id or ""),
            str(chat_id or ""),
            str(role or ""),
            str(image_status or ""),
            str(source or ""),
            bool(include_deleted),
        )

    async def update_message_record(
        self,
        selector: dict[str, Any],
        updates: dict[str, Any],
        *,
        reason: str = "",
        db_scope: str = "all",
    ) -> dict[str, Any]:
        if not self._started:
            await self.start()
        await self.flush()
        return await asyncio.to_thread(
            self._update_message_record_sync,
            dict(selector or {}),
            dict(updates or {}),
            str(reason or ""),
            str(db_scope or "all"),
        )

    async def soft_delete_messages(
        self,
        selectors: list[dict[str, Any]],
        *,
        reason: str = "",
        db_scope: str = "all",
    ) -> dict[str, Any]:
        if not self._started:
            await self.start()
        await self.flush()
        return await asyncio.to_thread(
            self._set_deleted_messages_sync,
            [dict(item or {}) for item in selectors],
            time.time(),
            str(reason or ""),
            str(db_scope or "all"),
        )

    async def restore_messages(
        self,
        selectors: list[dict[str, Any]],
        *,
        db_scope: str = "all",
    ) -> dict[str, Any]:
        if not self._started:
            await self.start()
        await self.flush()
        return await asyncio.to_thread(
            self._set_deleted_messages_sync,
            [dict(item or {}) for item in selectors],
            0.0,
            "",
            str(db_scope or "all"),
        )

    async def _writer_loop(self) -> None:
        batch: list[dict[str, Any]] = []
        last_flush = time.time()
        while True:
            timeout = max(0.1, self.flush_interval_seconds - (time.time() - last_flush))
            item = None
            try:
                item = await asyncio.wait_for(self._queue.get(), timeout=timeout)
            except asyncio.TimeoutError:
                item = "__timeout__"

            if item is None:
                if batch:
                    await self._flush_batch(batch)
                    batch = []
                self._queue.task_done()
                return

            if (
                isinstance(item, tuple)
                and len(item) == 2
                and item[0] is self._flush_sentinel
            ):
                if batch:
                    await self._flush_batch(batch)
                    batch = []
                    last_flush = time.time()
                item[1].set()
                self._queue.task_done()
                continue

            if item != "__timeout__":
                batch.append(item)
                self._queue.task_done()

            if batch and (
                len(batch) >= self.flush_batch_size
                or item == "__timeout__"
                or (time.time() - last_flush) >= self.flush_interval_seconds
            ):
                await self._flush_batch(batch)
                batch = []
                last_flush = time.time()

    async def _flush_batch(self, batch: list[dict[str, Any]]) -> None:
        try:
            await asyncio.to_thread(self._insert_messages_sync, list(batch))
            if DEBUG_MODE:
                logger.info("[GCP上下文存储] 已批量写入 %d 条消息", len(batch))
        except Exception as e:
            self._record_error("flush_batch", e)
            logger.error("[GCP上下文存储] 批量写入失败: %s", e, exc_info=True)

    async def _maintenance_loop(self) -> None:
        """周期性归档循环：把热库超期消息归档到冷库，并清理冷库过期数据。

        修复点：之前 SQLite 自存储只在插件 `initialize()` 时跑过一次维护，
        长时间运行的实例不会每天归档热库到冷库。该循环会按
        `maintenance_interval_seconds` 持续触发 `run_maintenance()`，
        即便单次维护抛错也会记录后继续等待下一次执行。
        """
        try:
            # 启动延迟：避免和 initialize() 中的首次维护抢锁
            if self.maintenance_initial_delay_seconds > 0:
                await asyncio.sleep(self.maintenance_initial_delay_seconds)
            while True:
                try:
                    await self.run_maintenance()
                    self._last_maintenance_at = time.time()
                except asyncio.CancelledError:
                    raise
                except Exception as e:
                    self._record_error("maintenance_loop", e)
                    logger.error(
                        "[GCP上下文存储] 周期性归档失败，将在下个周期重试: %s",
                        e,
                        exc_info=True,
                    )
                self._next_maintenance_at = time.time() + self.maintenance_interval_seconds
                await asyncio.sleep(self.maintenance_interval_seconds)
        except asyncio.CancelledError:
            return


    def _connect(self, db_path: Path) -> sqlite3.Connection:
        conn = sqlite3.connect(str(db_path), timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA busy_timeout=30000")
        conn.execute("PRAGMA temp_store=MEMORY")
        return conn

    @contextmanager
    def _connection(self, db_path: Path):
        conn = self._connect(db_path)
        try:
            yield conn
        finally:
            conn.close()

    def _initialize_sync(self) -> None:
        for db_path in (self.hot_db_path, self.cold_db_path):
            with self._connection(db_path) as conn:
                self._create_schema(conn, cold=(db_path == self.cold_db_path))
                conn.commit()

    def _create_schema(self, conn: sqlite3.Connection, *, cold: bool) -> None:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id TEXT NOT NULL,
                platform_name TEXT NOT NULL,
                platform_id TEXT NOT NULL,
                chat_id TEXT NOT NULL,
                chat_key TEXT NOT NULL,
                chat_type TEXT NOT NULL,
                role TEXT NOT NULL,
                sender_id TEXT NOT NULL,
                sender_name TEXT NOT NULL,
                timestamp REAL NOT NULL,
                content TEXT NOT NULL,
                reply_to_message_id TEXT DEFAULT '',
                image_refs_json TEXT DEFAULT '[]',
                image_descriptions_json TEXT DEFAULT '[]',
                image_status TEXT DEFAULT '',
                trigger_source TEXT DEFAULT '',
                probability_filtered INTEGER DEFAULT 0,
                wait_window_message INTEGER DEFAULT 0,
                raw_json TEXT DEFAULT '{}',
                created_at REAL NOT NULL,
                deleted_at REAL DEFAULT 0,
                deleted_reason TEXT DEFAULT '',
                edited_at REAL DEFAULT 0,
                edit_reason TEXT DEFAULT '',
                UNIQUE(platform_id, chat_id, message_id, role)
            );
            CREATE INDEX IF NOT EXISTS idx_messages_chat_ts
                ON messages(platform_id, chat_id, timestamp);
            CREATE INDEX IF NOT EXISTS idx_messages_chat_key_ts
                ON messages(chat_key, timestamp);

            CREATE TABLE IF NOT EXISTS image_status (
                image_key TEXT PRIMARY KEY,
                platform_id TEXT NOT NULL,
                chat_id TEXT NOT NULL,
                chat_key TEXT NOT NULL,
                message_id TEXT NOT NULL,
                image_ref TEXT NOT NULL,
                status TEXT NOT NULL,
                description TEXT DEFAULT '',
                failure_reason TEXT DEFAULT '',
                retry_count INTEGER DEFAULT 0,
                no_auto_retry INTEGER DEFAULT 0,
                updated_at REAL NOT NULL,
                created_at REAL NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_image_status_msg
                ON image_status(platform_id, chat_id, message_id, status);
            CREATE INDEX IF NOT EXISTS idx_image_status_chat
                ON image_status(platform_id, chat_id, status);
            """
        )
        self._ensure_message_columns(conn)
        if cold:
            try:
                conn.execute(
                    "CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts "
                    "USING fts5(content, sender_name, chat_key, content='messages', content_rowid='id')"
                )
                self._fts_available = True
            except sqlite3.DatabaseError as e:
                self._fts_available = False
                self._record_error("create_fts5", e)

    def _ensure_message_columns(self, conn: sqlite3.Connection) -> None:
        existing = {
            str(row["name"])
            for row in conn.execute("PRAGMA table_info(messages)").fetchall()
        }
        required = {
            "deleted_at": "REAL DEFAULT 0",
            "deleted_reason": "TEXT DEFAULT ''",
            "edited_at": "REAL DEFAULT 0",
            "edit_reason": "TEXT DEFAULT ''",
        }
        for column, definition in required.items():
            if column not in existing:
                conn.execute(f"ALTER TABLE messages ADD COLUMN {column} {definition}")

    def _normalize_message(self, msg: dict[str, Any]) -> dict[str, Any]:
        platform_id = str(msg.get("platform_id") or "")
        platform_name = str(msg.get("platform_name") or "")
        chat_id = str(msg.get("chat_id") or "")
        chat_type = str(msg.get("chat_type") or "group")
        chat_key = str(msg.get("chat_key") or f"{platform_id}:{chat_id}")
        message_id = str(msg.get("message_id") or f"gcp_{time.time_ns()}")
        role = str(msg.get("role") or "user")
        timestamp = msg.get("timestamp")
        try:
            timestamp = float(timestamp)
        except Exception:
            timestamp = time.time()
        content = str(msg.get("content") or "")
        image_refs = msg.get("image_refs") or msg.get("image_urls") or []
        if not isinstance(image_refs, list):
            image_refs = [str(image_refs)]
        image_descriptions = msg.get("image_descriptions") or []
        if not isinstance(image_descriptions, list):
            image_descriptions = [str(image_descriptions)]
        return {
            "message_id": message_id,
            "platform_name": platform_name,
            "platform_id": platform_id,
            "chat_id": chat_id,
            "chat_key": chat_key,
            "chat_type": chat_type,
            "role": role,
            "sender_id": str(msg.get("sender_id") or ""),
            "sender_name": str(msg.get("sender_name") or ""),
            "timestamp": timestamp,
            "content": content,
            "reply_to_message_id": str(msg.get("reply_to_message_id") or ""),
            "image_refs_json": json.dumps(image_refs, ensure_ascii=False),
            "image_descriptions_json": json.dumps(image_descriptions, ensure_ascii=False),
            "image_status": str(msg.get("image_status") or ""),
            "trigger_source": str(msg.get("trigger_source") or ""),
            "probability_filtered": 1 if msg.get("probability_filtered") else 0,
            "wait_window_message": 1 if msg.get("wait_window_message") or msg.get("window_buffered") else 0,
            "raw_json": json.dumps(msg, ensure_ascii=False, default=str),
            "created_at": time.time(),
            "deleted_at": float(msg.get("deleted_at") or 0),
            "deleted_reason": str(msg.get("deleted_reason") or ""),
            "edited_at": float(msg.get("edited_at") or 0),
            "edit_reason": str(msg.get("edit_reason") or ""),
        }

    def _insert_messages_sync(self, messages: list[dict[str, Any]]) -> None:
        if not messages:
            return
        rows = [self._normalize_message(m) for m in messages if m]
        if not rows:
            return
        with self._connection(self.hot_db_path) as conn:
            conn.executemany(
                """
                INSERT OR REPLACE INTO messages (
                    message_id, platform_name, platform_id, chat_id, chat_key,
                    chat_type, role, sender_id, sender_name, timestamp, content,
                    reply_to_message_id, image_refs_json, image_descriptions_json,
                    image_status, trigger_source, probability_filtered,
                    wait_window_message, raw_json, created_at,
                    deleted_at, deleted_reason, edited_at, edit_reason
                ) VALUES (
                    :message_id, :platform_name, :platform_id, :chat_id, :chat_key,
                    :chat_type, :role, :sender_id, :sender_name, :timestamp, :content,
                    :reply_to_message_id, :image_refs_json, :image_descriptions_json,
                    :image_status, :trigger_source, :probability_filtered,
                    :wait_window_message, :raw_json, :created_at,
                    :deleted_at, :deleted_reason, :edited_at, :edit_reason
                )
                """,
                rows,
            )
            conn.commit()

    def _row_to_message(self, row: sqlite3.Row) -> StoredMessage:
        def load_list(value: str) -> list[str]:
            try:
                parsed = json.loads(value or "[]")
                if isinstance(parsed, list):
                    return [str(x) for x in parsed if x is not None]
            except Exception:
                pass
            return []

        raw_json: dict[str, Any] = {}
        try:
            parsed_raw = json.loads(row["raw_json"] or "{}")
            if isinstance(parsed_raw, dict):
                raw_json = parsed_raw
        except Exception:
            raw_json = {}
        image_items = raw_json.get("image_items") or raw_json.get("image_metadata") or []
        if not isinstance(image_items, list):
            image_items = []

        return StoredMessage(
            message_id=str(row["message_id"] or ""),
            platform_name=str(row["platform_name"] or ""),
            platform_id=str(row["platform_id"] or ""),
            chat_id=str(row["chat_id"] or ""),
            chat_key=str(row["chat_key"] or ""),
            chat_type=str(row["chat_type"] or "group"),
            role=str(row["role"] or "user"),
            sender_id=str(row["sender_id"] or ""),
            sender_name=str(row["sender_name"] or ""),
            timestamp=float(row["timestamp"] or 0),
            content=str(row["content"] or ""),
            reply_to_message_id=str(row["reply_to_message_id"] or ""),
            image_refs=load_list(row["image_refs_json"]),
            image_descriptions=load_list(row["image_descriptions_json"]),
            image_status=str(row["image_status"] or ""),
            trigger_source=str(row["trigger_source"] or ""),
            probability_filtered=bool(row["probability_filtered"]),
            wait_window_message=bool(row["wait_window_message"]),
            deleted_at=float(row["deleted_at"] or 0),
            deleted_reason=str(row["deleted_reason"] or ""),
            edited_at=float(row["edited_at"] or 0),
            edit_reason=str(row["edit_reason"] or ""),
            image_items=[item for item in image_items if isinstance(item, dict)],
            raw_json=raw_json,
        )

    def _get_recent_messages_sync(
        self,
        platform_id: str,
        chat_id: str,
        limit: int,
        include_cold: bool,
    ) -> list[StoredMessage]:
        if limit == 0:
            return []
        effective_limit = 500 if limit < 0 else max(1, min(limit, 500))
        rows: list[StoredMessage] = []
        with self._connection(self.hot_db_path) as conn:
            cur = conn.execute(
                """
                SELECT * FROM messages
                WHERE platform_id=? AND chat_id=? AND COALESCE(deleted_at, 0)=0
                ORDER BY timestamp DESC, id DESC
                LIMIT ?
                """,
                (platform_id, chat_id, effective_limit),
            )
            rows.extend(self._row_to_message(r) for r in cur.fetchall())

        if include_cold and len(rows) < effective_limit:
            remaining = effective_limit - len(rows)
            existing_ids = {m.message_id for m in rows}
            with self._connection(self.cold_db_path) as conn:
                cur = conn.execute(
                    """
                    SELECT * FROM messages
                    WHERE platform_id=? AND chat_id=? AND COALESCE(deleted_at, 0)=0
                    ORDER BY timestamp DESC, id DESC
                    LIMIT ?
                    """,
                    (platform_id, chat_id, remaining),
                )
                for row in cur.fetchall():
                    msg = self._row_to_message(row)
                    if msg.message_id not in existing_ids:
                        rows.append(msg)

        rows.sort(key=lambda m: (m.timestamp, m.message_id))
        return rows[-effective_limit:]

    def _get_messages_by_ids_sync(
        self,
        platform_id: str,
        chat_id: str,
        message_ids: list[str],
        include_cold: bool,
    ) -> dict[str, StoredMessage]:
        if not platform_id or not chat_id or not message_ids:
            return {}

        result: dict[str, StoredMessage] = {}

        def fetch_from(db_path: Path, ids: list[str]) -> None:
            if not ids:
                return
            placeholders = ",".join("?" for _ in ids)
            with self._connection(db_path) as conn:
                rows = conn.execute(
                    f"""
                    SELECT * FROM messages
                    WHERE platform_id=? AND chat_id=?
                      AND message_id IN ({placeholders})
                      AND COALESCE(deleted_at, 0)=0
                    ORDER BY timestamp DESC, id DESC
                    """,
                    (platform_id, chat_id, *ids),
                ).fetchall()
                for row in rows:
                    msg = self._row_to_message(row)
                    if msg.message_id not in result:
                        result[msg.message_id] = msg

        fetch_from(self.hot_db_path, message_ids)
        if include_cold:
            missing = [mid for mid in message_ids if mid not in result]
            fetch_from(self.cold_db_path, missing)
        return result

    def _run_maintenance_sync(self) -> None:
        cutoff_hot = time.time() - self.hot_retention_days * 86400
        cutoff_cold = time.time() - self.cold_retention_days * 86400
        moved = 0
        deleted = 0
        with self._connection(self.hot_db_path) as hot, self._connection(self.cold_db_path) as cold:
            old_rows = hot.execute(
                "SELECT * FROM messages WHERE timestamp < ? ORDER BY timestamp ASC",
                (cutoff_hot,),
            ).fetchall()
            if old_rows:
                payload = []
                for row in old_rows:
                    payload.append({k: row[k] for k in row.keys()})
                cold.executemany(
                    """
                    INSERT OR IGNORE INTO messages (
                        message_id, platform_name, platform_id, chat_id, chat_key,
                        chat_type, role, sender_id, sender_name, timestamp, content,
                        reply_to_message_id, image_refs_json, image_descriptions_json,
                        image_status, trigger_source, probability_filtered,
                        wait_window_message, raw_json, created_at,
                        deleted_at, deleted_reason, edited_at, edit_reason
                    ) VALUES (
                        :message_id, :platform_name, :platform_id, :chat_id, :chat_key,
                        :chat_type, :role, :sender_id, :sender_name, :timestamp, :content,
                        :reply_to_message_id, :image_refs_json, :image_descriptions_json,
                        :image_status, :trigger_source, :probability_filtered,
                        :wait_window_message, :raw_json, :created_at,
                        :deleted_at, :deleted_reason, :edited_at, :edit_reason
                    )
                    """,
                    payload,
                )
                moved = len(old_rows)
                hot.execute("DELETE FROM messages WHERE timestamp < ?", (cutoff_hot,))

            deleted += cold.execute(
                "DELETE FROM messages WHERE timestamp < ?",
                (cutoff_cold,),
            ).rowcount

            chat_rows = cold.execute(
                "SELECT DISTINCT platform_id, chat_id FROM messages"
            ).fetchall()
            for chat in chat_rows:
                total = cold.execute(
                    "SELECT COUNT(*) FROM messages WHERE platform_id=? AND chat_id=?",
                    (chat["platform_id"], chat["chat_id"]),
                ).fetchone()[0]
                over = int(total) - self.cold_max_messages_per_chat
                if over > 0:
                    deleted += cold.execute(
                        """
                        DELETE FROM messages
                        WHERE id IN (
                            SELECT id FROM messages
                            WHERE platform_id=? AND chat_id=?
                            ORDER BY timestamp ASC, id ASC
                            LIMIT ?
                        )
                        """,
                        (chat["platform_id"], chat["chat_id"], over),
                    ).rowcount

            if self._fts_available:
                try:
                    cold.execute("DELETE FROM messages_fts")
                    cold.execute(
                        """
                        INSERT INTO messages_fts(rowid, content, sender_name, chat_key)
                        SELECT id, content, sender_name, chat_key FROM messages
                        """
                    )
                except sqlite3.DatabaseError as e:
                    self._record_error("rebuild_fts", e)

            hot.commit()
            cold.commit()

        logger.info(
            "[GCP上下文存储] 归档完成 moved_to_cold=%d deleted_from_cold=%d",
            moved,
            deleted,
        )

    def _upsert_image_status_sync(self, image: dict[str, Any]) -> None:
        now = time.time()
        image_key = str(image.get("image_key") or "")
        if not image_key:
            return
        row = {
            "image_key": image_key,
            "platform_id": str(image.get("platform_id") or ""),
            "chat_id": str(image.get("chat_id") or ""),
            "chat_key": str(image.get("chat_key") or ""),
            "message_id": str(image.get("message_id") or ""),
            "image_ref": str(image.get("image_ref") or ""),
            "status": str(image.get("status") or "pending_retry"),
            "description": str(image.get("description") or ""),
            "failure_reason": str(image.get("failure_reason") or ""),
            "retry_count": int(image.get("retry_count") or 0),
            "no_auto_retry": 1 if image.get("no_auto_retry") else 0,
            "updated_at": now,
            "created_at": now,
        }
        with self._connection(self.hot_db_path) as conn:
            conn.execute(
                """
                INSERT INTO image_status (
                    image_key, platform_id, chat_id, chat_key, message_id, image_ref,
                    status, description, failure_reason, retry_count, no_auto_retry,
                    updated_at, created_at
                ) VALUES (
                    :image_key, :platform_id, :chat_id, :chat_key, :message_id, :image_ref,
                    :status, :description, :failure_reason, :retry_count, :no_auto_retry,
                    :updated_at, :created_at
                )
                ON CONFLICT(image_key) DO UPDATE SET
                    status=excluded.status,
                    description=excluded.description,
                    failure_reason=excluded.failure_reason,
                    retry_count=excluded.retry_count,
                    no_auto_retry=excluded.no_auto_retry,
                    updated_at=excluded.updated_at
                """,
                row,
            )
            conn.commit()

    def _get_pending_images_for_message_sync(
        self,
        platform_id: str,
        chat_id: str,
        message_id: str,
    ) -> list[dict[str, Any]]:
        if not message_id:
            return []
        with self._connection(self.hot_db_path) as conn:
            cur = conn.execute(
                """
                SELECT * FROM image_status
                WHERE platform_id=? AND chat_id=? AND message_id=?
                  AND status IN ('pending_retry', 'skipped_spam_batch')
                  AND no_auto_retry=0
                ORDER BY created_at ASC
                """,
                (platform_id, chat_id, message_id),
            )
            return [dict(row) for row in cur.fetchall()]

    def _update_image_status_sync(
        self,
        image_key: str,
        status: str,
        description: str,
        failure_reason: str,
        retry_increment: int,
    ) -> None:
        if not image_key:
            return
        with self._connection(self.hot_db_path) as conn:
            conn.execute(
                """
                UPDATE image_status
                SET status=?, description=?, failure_reason=?,
                    retry_count=retry_count + ?, no_auto_retry=?,
                    updated_at=?
                WHERE image_key=?
                """,
                (
                    status,
                    description or "",
                    failure_reason or "",
                    retry_increment,
                    1 if status == "failed_final" else 0,
                    time.time(),
                    image_key,
                ),
            )
            conn.commit()

    def _update_message_image_result_sync(
        self,
        platform_id: str,
        chat_id: str,
        message_id: str,
        image_ref: str,
        status: str,
        description: str,
        failure_reason: str,
    ) -> None:
        if not platform_id or not chat_id or not status:
            return

        for db_path in (self.hot_db_path, self.cold_db_path):
            with self._connection(db_path) as conn:
                self._update_message_image_result_in_conn(
                    conn,
                    platform_id,
                    chat_id,
                    message_id,
                    image_ref,
                    status,
                    description,
                    failure_reason,
                )

    @staticmethod
    def _merge_image_update_raw_json(
        raw_json_text: str,
        *,
        image_ref: str,
        status: str,
        description: str,
        failure_reason: str,
        descriptions: list[str],
    ) -> str:
        payload: dict[str, Any] = {}
        try:
            parsed = json.loads(raw_json_text or "{}")
            if isinstance(parsed, dict):
                payload = parsed
        except Exception:
            payload = {}

        updates = payload.get("image_updates")
        if not isinstance(updates, list):
            updates = []
        updates.append(
            {
                "image_ref": image_ref,
                "status": status,
                "description": description,
                "failure_reason": failure_reason,
                "updated_at": time.time(),
            }
        )
        payload["image_updates"] = updates
        payload["image_status"] = status
        if descriptions:
            payload["image_descriptions"] = descriptions
        return json.dumps(payload, ensure_ascii=False, default=str)

    def _update_message_image_result_in_conn(
        self,
        conn: sqlite3.Connection,
        platform_id: str,
        chat_id: str,
        message_id: str,
        image_ref: str,
        status: str,
        description: str,
        failure_reason: str,
    ) -> None:
        like_ref = f"%{image_ref}%" if image_ref else ""
        where_extra = " OR image_refs_json LIKE ?" if like_ref else ""
        params: list[Any] = [platform_id, chat_id, message_id]
        if like_ref:
            params.append(like_ref)

        rows = conn.execute(
            f"""
            SELECT id, content, image_descriptions_json, raw_json FROM messages
            WHERE platform_id=? AND chat_id=?
              AND (message_id=?{where_extra})
            ORDER BY timestamp DESC, id DESC
            LIMIT 10
            """,
            tuple(params),
        ).fetchall()
        if not rows:
            return

        for row in rows:
            content = str(row["content"] or "")
            descriptions: list[str] = []
            try:
                parsed = json.loads(row["image_descriptions_json"] or "[]")
                if isinstance(parsed, list):
                    descriptions = [str(x) for x in parsed if x is not None]
            except Exception:
                descriptions = []

            if status == "success":
                if description and description not in descriptions:
                    descriptions.append(description)
                replacement = f"[图片内容: {description}]" if description else "[图片已识别]"
                if "[图片（识别失败）]" in content:
                    content = content.replace("[图片（识别失败）]", replacement, 1)
                elif "[图片]" in content and description:
                    content = content.replace("[图片]", replacement, 1)
                elif description and description not in content:
                    content = f"{content}\n{replacement}".strip()
            elif status == "failed_final":
                reason_text = f": {failure_reason}" if failure_reason else ""
                replacement = f"[图片最终识别失败{reason_text}]"
                if "[图片（识别失败）]" in content:
                    content = content.replace("[图片（识别失败）]", replacement, 1)
                elif "[图片]" in content:
                    content = content.replace("[图片]", replacement, 1)
                elif replacement not in content:
                    content = f"{content}\n{replacement}".strip()

            conn.execute(
                """
                UPDATE messages
                SET content=?, image_descriptions_json=?, image_status=?, raw_json=?
                WHERE id=?
                """,
                (
                    content,
                    json.dumps(descriptions, ensure_ascii=False),
                    status,
                    self._merge_image_update_raw_json(
                        row["raw_json"],
                        image_ref=image_ref,
                        status=status,
                        description=description,
                        failure_reason=failure_reason,
                        descriptions=descriptions,
                    ),
                    row["id"],
                ),
            )
        conn.commit()

    def _get_status_sync(self, platform_id: str, chat_id: str) -> dict[str, Any]:
        result: dict[str, Any] = {
            "hot_messages": 0,
            "cold_messages": 0,
            "image_success": 0,
            "image_pending_retry": 0,
            "image_failed_final": 0,
            "hot_db": str(self.hot_db_path),
            "cold_db": str(self.cold_db_path),
        }
        where = ""
        params: tuple[Any, ...] = ()
        if platform_id and chat_id:
            where = " WHERE platform_id=? AND chat_id=?"
            params = (platform_id, chat_id)

        with self._connection(self.hot_db_path) as conn:
            result["hot_messages"] = conn.execute(
                f"SELECT COUNT(*) FROM messages{where}"
                + (" AND " if where else " WHERE ")
                + "COALESCE(deleted_at, 0)=0",
                params,
            ).fetchone()[0]
            result["hot_deleted_messages"] = conn.execute(
                f"SELECT COUNT(*) FROM messages{where}"
                + (" AND " if where else " WHERE ")
                + "COALESCE(deleted_at, 0)>0",
                params,
            ).fetchone()[0]
            img_where = where
            result["image_success"] = conn.execute(
                f"SELECT COUNT(*) FROM image_status{img_where} "
                + ("AND " if img_where else "WHERE ")
                + "status='success'",
                params,
            ).fetchone()[0]
            result["image_pending_retry"] = conn.execute(
                f"SELECT COUNT(*) FROM image_status{img_where} "
                + ("AND " if img_where else "WHERE ")
                + "status='pending_retry'",
                params,
            ).fetchone()[0]
            result["image_failed_final"] = conn.execute(
                f"SELECT COUNT(*) FROM image_status{img_where} "
                + ("AND " if img_where else "WHERE ")
                + "status='failed_final'",
                params,
            ).fetchone()[0]

        with self._connection(self.cold_db_path) as conn:
            result["cold_messages"] = conn.execute(
                f"SELECT COUNT(*) FROM messages{where}"
                + (" AND " if where else " WHERE ")
                + "COALESCE(deleted_at, 0)=0",
                params,
            ).fetchone()[0]
            result["cold_deleted_messages"] = conn.execute(
                f"SELECT COUNT(*) FROM messages{where}"
                + (" AND " if where else " WHERE ")
                + "COALESCE(deleted_at, 0)>0",
                params,
            ).fetchone()[0]
        return result

    def _db_paths_for_scope(self, db_scope: str) -> list[tuple[str, Path]]:
        scope = str(db_scope or "hot").lower()
        if scope == "hot":
            return [("hot", self.hot_db_path)]
        if scope == "cold":
            return [("cold", self.cold_db_path)]
        if scope != "all":
            raise ValueError("db_scope 必须是 hot、cold 或 all")
        return [("hot", self.hot_db_path), ("cold", self.cold_db_path)]

    def _message_row_to_dict(self, row: sqlite3.Row, db_name: str) -> dict[str, Any]:
        def load_list(value: str) -> list[str]:
            try:
                parsed = json.loads(value or "[]")
                if isinstance(parsed, list):
                    return [str(item) for item in parsed if item is not None]
            except Exception:
                pass
            return []

        raw_json: Any = {}
        try:
            raw_json = json.loads(row["raw_json"] or "{}")
        except Exception:
            raw_json = {}

        return {
            "db": db_name,
            "id": int(row["id"]),
            "message_id": str(row["message_id"] or ""),
            "platform_name": str(row["platform_name"] or ""),
            "platform_id": str(row["platform_id"] or ""),
            "chat_id": str(row["chat_id"] or ""),
            "chat_key": str(row["chat_key"] or ""),
            "chat_type": str(row["chat_type"] or ""),
            "role": str(row["role"] or ""),
            "sender_id": str(row["sender_id"] or ""),
            "sender_name": str(row["sender_name"] or ""),
            "timestamp": float(row["timestamp"] or 0),
            "content": str(row["content"] or ""),
            "reply_to_message_id": str(row["reply_to_message_id"] or ""),
            "image_refs": load_list(row["image_refs_json"]),
            "image_descriptions": load_list(row["image_descriptions_json"]),
            "image_status": str(row["image_status"] or ""),
            "image_items": raw_json.get("image_items")
            if isinstance(raw_json.get("image_items"), list)
            else [],
            "trigger_source": str(row["trigger_source"] or ""),
            "probability_filtered": bool(row["probability_filtered"]),
            "wait_window_message": bool(row["wait_window_message"]),
            "raw_json": raw_json,
            "created_at": float(row["created_at"] or 0),
            "deleted_at": float(row["deleted_at"] or 0),
            "deleted_reason": str(row["deleted_reason"] or ""),
            "edited_at": float(row["edited_at"] or 0),
            "edit_reason": str(row["edit_reason"] or ""),
        }

    def _build_list_where(
        self,
        *,
        keyword: str,
        platform_id: str,
        chat_id: str,
        role: str,
        image_status: str,
        source: str,
        include_deleted: bool,
    ) -> tuple[str, list[Any]]:
        clauses: list[str] = []
        params: list[Any] = []

        if not include_deleted:
            clauses.append("COALESCE(deleted_at, 0)=0")
        if platform_id:
            clauses.append("platform_id=?")
            params.append(platform_id)
        if chat_id:
            clauses.append("chat_id=?")
            params.append(chat_id)
        if role and role != "all":
            clauses.append("role=?")
            params.append(role)
        if image_status and image_status != "all":
            clauses.append("image_status=?")
            params.append(image_status)
        if source and source != "all":
            clauses.append("trigger_source=?")
            params.append(source)
        if keyword:
            like = f"%{keyword}%"
            if keyword.isdigit():
                clauses.append(
                    "(CAST(id AS TEXT)=? OR message_id LIKE ? OR sender_id LIKE ? "
                    "OR sender_name LIKE ? COLLATE NOCASE OR content LIKE ? COLLATE NOCASE)"
                )
                params.extend([keyword, like, like, like, like])
            else:
                clauses.append(
                    "(message_id LIKE ? OR sender_id LIKE ? OR sender_name LIKE ? COLLATE NOCASE "
                    "OR content LIKE ? COLLATE NOCASE OR chat_id LIKE ? OR platform_id LIKE ?)"
                )
                params.extend([like, like, like, like, like, like])

        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        return where, params

    def _list_messages_sync(
        self,
        page: int,
        page_size: int,
        db_scope: str,
        keyword: str,
        platform_id: str,
        chat_id: str,
        role: str,
        image_status: str,
        source: str,
        include_deleted: bool,
    ) -> dict[str, Any]:
        page = max(1, page)
        page_size = min(200, max(1, page_size))
        where, params = self._build_list_where(
            keyword=keyword.strip(),
            platform_id=platform_id.strip(),
            chat_id=chat_id.strip(),
            role=role.strip(),
            image_status=image_status.strip(),
            source=source.strip(),
            include_deleted=include_deleted,
        )

        combined: list[dict[str, Any]] = []
        totals: dict[str, int] = {}
        for db_name, db_path in self._db_paths_for_scope(db_scope):
            with self._connection(db_path) as conn:
                total = int(
                    conn.execute(
                        f"SELECT COUNT(*) FROM messages {where}",
                        tuple(params),
                    ).fetchone()[0]
                )
                totals[db_name] = total
                if db_scope.lower() in {"hot", "cold"}:
                    offset = (page - 1) * page_size
                    rows = conn.execute(
                        f"""
                        SELECT * FROM messages
                        {where}
                        ORDER BY timestamp DESC, id DESC
                        LIMIT ? OFFSET ?
                        """,
                        (*params, page_size, offset),
                    ).fetchall()
                    combined.extend(
                        self._message_row_to_dict(row, db_name) for row in rows
                    )
                else:
                    rows = conn.execute(
                        f"""
                        SELECT * FROM messages
                        {where}
                        ORDER BY timestamp DESC, id DESC
                        LIMIT ?
                        """,
                        (*params, page * page_size),
                    ).fetchall()
                    combined.extend(
                        self._message_row_to_dict(row, db_name) for row in rows
                    )

        total = sum(totals.values())
        if str(db_scope or "hot").lower() not in {"hot", "cold"}:
            combined.sort(key=lambda item: (item["timestamp"], item["id"]), reverse=True)
            start = (page - 1) * page_size
            combined = combined[start : start + page_size]

        return {
            "items": combined,
            "total": total,
            "page": page,
            "page_size": page_size,
            "has_more": page * page_size < total,
            "db_totals": totals,
        }

    def _selector_where(self, selector: dict[str, Any]) -> tuple[str, list[Any]]:
        if selector.get("id") not in (None, ""):
            return "id=?", [int(selector["id"])]

        platform_id = str(selector.get("platform_id") or "")
        chat_id = str(selector.get("chat_id") or "")
        message_id = str(selector.get("message_id") or "")
        role = str(selector.get("role") or "")
        if not platform_id or not chat_id or not message_id:
            raise ValueError("selector 需要 id 或 platform_id+chat_id+message_id")

        clauses = ["platform_id=?", "chat_id=?", "message_id=?"]
        params: list[Any] = [platform_id, chat_id, message_id]
        if role:
            clauses.append("role=?")
            params.append(role)
        return " AND ".join(clauses), params

    def _update_message_record_sync(
        self,
        selector: dict[str, Any],
        updates: dict[str, Any],
        reason: str,
        db_scope: str,
    ) -> dict[str, Any]:
        allowed_fields = {
            "content": "content",
            "sender_name": "sender_name",
            "image_status": "image_status",
        }
        set_parts: list[str] = []
        params: list[Any] = []
        for api_field, db_field in allowed_fields.items():
            if api_field in updates:
                set_parts.append(f"{db_field}=?")
                params.append(str(updates.get(api_field) or ""))

        if "image_descriptions" in updates:
            descriptions = updates.get("image_descriptions") or []
            if isinstance(descriptions, str):
                descriptions = [
                    line.strip()
                    for line in descriptions.splitlines()
                    if line.strip()
                ]
            if not isinstance(descriptions, list):
                raise ValueError("image_descriptions 必须是数组或多行字符串")
            set_parts.append("image_descriptions_json=?")
            params.append(json.dumps([str(x) for x in descriptions], ensure_ascii=False))

        if not set_parts:
            return {"updated_count": 0}

        set_parts.extend(["edited_at=?", "edit_reason=?"])
        params.extend([time.time(), reason])
        where, where_params = self._selector_where(selector)
        params.extend(where_params)

        updated = 0
        for _, db_path in self._db_paths_for_scope(db_scope):
            with self._connection(db_path) as conn:
                updated += conn.execute(
                    f"UPDATE messages SET {', '.join(set_parts)} WHERE {where}",
                    tuple(params),
                ).rowcount
                conn.commit()
        return {"updated_count": updated}

    def _set_deleted_messages_sync(
        self,
        selectors: list[dict[str, Any]],
        deleted_at: float,
        reason: str,
        db_scope: str,
    ) -> dict[str, Any]:
        updated = 0
        failed: list[dict[str, Any]] = []
        for selector in selectors:
            try:
                where, params = self._selector_where(selector)
                for _, db_path in self._db_paths_for_scope(db_scope):
                    with self._connection(db_path) as conn:
                        updated += conn.execute(
                            f"""
                            UPDATE messages
                            SET deleted_at=?, deleted_reason=?
                            WHERE {where}
                            """,
                            (deleted_at, reason, *params),
                        ).rowcount
                        conn.commit()
            except Exception as exc:
                failed.append({"selector": selector, "error": str(exc)})

        return {
            "updated_count": updated,
            "failed_count": len(failed),
            "failed": failed,
        }

    def _clear_chat_sync(self, platform_id: str, chat_id: str) -> None:
        for db_path in (self.hot_db_path, self.cold_db_path):
            with self._connection(db_path) as conn:
                conn.execute(
                    "DELETE FROM messages WHERE platform_id=? AND chat_id=?",
                    (platform_id, chat_id),
                )
                conn.execute(
                    "DELETE FROM image_status WHERE platform_id=? AND chat_id=?",
                    (platform_id, chat_id),
                )
                conn.commit()

    def _clear_all_sync(self) -> None:
        for db_path in (self.hot_db_path, self.cold_db_path):
            with self._connection(db_path) as conn:
                conn.execute("DELETE FROM messages")
                conn.execute("DELETE FROM image_status")
                if db_path == self.cold_db_path and self._fts_available:
                    try:
                        conn.execute("DELETE FROM messages_fts")
                    except sqlite3.DatabaseError:
                        pass
                conn.commit()

    def _record_error(self, operation: str, exc: Exception) -> None:
        text = f"{operation}: {type(exc).__name__}: {exc}"
        self._last_error = text[:500]
        self._recent_errors.append({"ts": time.time(), "error": self._last_error})
        self._recent_errors = self._recent_errors[-20:]

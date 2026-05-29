import asyncio
import importlib.util
import sqlite3
import sys
import time
import types
from pathlib import Path


def load_store_class():
    if "astrbot.api" not in sys.modules:
        astrbot_module = types.ModuleType("astrbot")
        api_module = types.ModuleType("astrbot.api")
        api_module.logger = types.SimpleNamespace(
            info=lambda *args, **kwargs: None,
            warning=lambda *args, **kwargs: None,
            error=lambda *args, **kwargs: None,
            debug=lambda *args, **kwargs: None,
        )
        sys.modules.setdefault("astrbot", astrbot_module)
        sys.modules["astrbot.api"] = api_module

    path = Path(__file__).resolve().parents[1] / "utils" / "sqlite_context_store.py"
    spec = importlib.util.spec_from_file_location("sqlite_context_store_under_test", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.SQLiteContextStore


SQLiteContextStore = load_store_class()


def run(coro):
    return asyncio.run(coro)


def base_message(message_id="m1", content="hello"):
    return {
        "message_id": message_id,
        "platform_name": "aiocqhttp",
        "platform_id": "qq",
        "chat_id": "100",
        "chat_key": "qq:100",
        "chat_type": "group",
        "role": "user",
        "sender_id": "u1",
        "sender_name": "Alice",
        "timestamp": time.time(),
        "content": content,
        "trigger_source": "normal",
    }


def test_schema_migration_adds_soft_delete_columns(tmp_path):
    store = SQLiteContextStore(tmp_path)
    store.base_dir.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(store.hot_db_path) as conn:
        conn.execute(
            """
            CREATE TABLE messages (
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
                UNIQUE(platform_id, chat_id, message_id, role)
            )
            """
        )
        conn.commit()

    async def scenario():
        await store.start()
        try:
            with sqlite3.connect(store.hot_db_path) as conn:
                columns = {row[1] for row in conn.execute("PRAGMA table_info(messages)")}
            assert {"deleted_at", "deleted_reason", "edited_at", "edit_reason"} <= columns
        finally:
            await store.close()

    run(scenario())


def test_soft_delete_filters_recent_and_restore_reenables(tmp_path):
    store = SQLiteContextStore(tmp_path)

    async def scenario():
        await store.start()
        await store.add_message_sync(base_message("m1", "visible"))
        assert [m.content for m in await store.get_recent_messages(platform_id="qq", chat_id="100", limit=10)] == ["visible"]

        await store.soft_delete_messages(
            [{"platform_id": "qq", "chat_id": "100", "message_id": "m1", "role": "user"}],
            reason="test",
        )
        assert await store.get_recent_messages(platform_id="qq", chat_id="100", limit=10) == []

        deleted = await store.list_messages(
            platform_id="qq",
            chat_id="100",
            include_deleted=True,
        )
        assert deleted["total"] == 1
        assert deleted["items"][0]["deleted_at"] > 0

        await store.restore_messages(
            [{"platform_id": "qq", "chat_id": "100", "message_id": "m1", "role": "user"}]
        )
        restored = await store.get_recent_messages(platform_id="qq", chat_id="100", limit=10)
        assert [m.content for m in restored] == ["visible"]
        await store.close()

    run(scenario())


def test_get_messages_by_ids_reads_hot_and_cold(tmp_path):
    store = SQLiteContextStore(tmp_path)

    async def scenario():
        await store.start()
        try:
            old = base_message("old-image", "[图片]")
            old["timestamp"] = time.time() - 10
            old["image_refs"] = ["old-ref"]
            old["image_status"] = "pending_retry"
            await store.add_message_sync(base_message("hot-image", "[图片内容: hot]"))
            await store.add_message_sync(old)

            hot_rows = await store.get_messages_by_ids(
                platform_id="qq",
                chat_id="100",
                message_ids=["hot-image"],
                include_cold=True,
            )
            assert hot_rows["hot-image"].content == "[图片内容: hot]"

            store.hot_retention_days = 0
            await store.run_maintenance()

            cold_rows = await store.get_messages_by_ids(
                platform_id="qq",
                chat_id="100",
                message_ids=["old-image"],
                include_cold=True,
            )
            assert cold_rows["old-image"].content == "[图片]"
            assert cold_rows["old-image"].image_refs == ["old-ref"]
        finally:
            await store.close()

    run(scenario())


def test_flush_persists_dequeued_writer_batch(tmp_path):
    store = SQLiteContextStore(
        tmp_path,
        flush_batch_size=100,
        flush_interval_seconds=60,
    )

    async def scenario():
        await store.start()
        try:
            await store.enqueue_message(base_message("queued-1", "queued content"))
            await asyncio.sleep(0)
            await store.flush()

            rows = await store.get_recent_messages(
                platform_id="qq",
                chat_id="100",
                limit=10,
            )
            assert [row.message_id for row in rows] == ["queued-1"]
        finally:
            await store.close()

    run(scenario())


def test_concurrent_start_only_creates_one_writer_and_maintenance_task(tmp_path, monkeypatch):
    store = SQLiteContextStore(tmp_path)
    real_initialize = store._initialize_sync
    calls = 0

    def slow_initialize():
        nonlocal calls
        calls += 1
        time.sleep(0.02)
        real_initialize()

    monkeypatch.setattr(store, "_initialize_sync", slow_initialize)

    async def scenario():
        await asyncio.gather(*(store.start() for _ in range(6)))
        try:
            assert calls == 1
            worker = store._worker_task
            maintenance = store._maintenance_task
            assert worker is not None and not worker.done()
            assert maintenance is not None and not maintenance.done()

            await asyncio.gather(*(store.start() for _ in range(3)))
            assert calls == 1
            assert store._worker_task is worker
            assert store._maintenance_task is maintenance
        finally:
            await store.close()

    run(scenario())


def test_close_waits_for_inflight_start_before_stopping(tmp_path, monkeypatch):
    store = SQLiteContextStore(tmp_path)
    real_initialize = store._initialize_sync
    calls = 0

    def slow_initialize():
        nonlocal calls
        calls += 1
        time.sleep(0.02)
        real_initialize()

    monkeypatch.setattr(store, "_initialize_sync", slow_initialize)

    async def scenario():
        start_task = asyncio.create_task(store.start())
        await asyncio.sleep(0)
        await store.close()
        await start_task

        assert calls == 1
        assert store._started is False
        assert store._worker_task is None
        assert store._maintenance_task is None

    run(scenario())


def test_image_metadata_round_trip_uses_raw_json(tmp_path):
    store = SQLiteContextStore(tmp_path)

    async def scenario():
        await store.start()
        try:
            msg = base_message("low-image", "[图片]")
            msg["image_refs"] = ["img-ref"]
            msg["image_descriptions"] = []
            msg["image_status"] = "success"
            msg["image_items"] = [
                {
                    "image_ref": "img-ref",
                    "description": "完整图片描述",
                    "importance": 0.2,
                    "effective_importance": 0.05,
                    "keep": False,
                    "gate_reason": "below_threshold",
                    "policy_version": "image_importance_gate_v1",
                }
            ]
            await store.add_message_sync(msg)

            rows = await store.get_recent_messages(
                platform_id="qq",
                chat_id="100",
                limit=10,
            )
            assert rows[0].content == "[图片]"
            assert rows[0].image_descriptions == []
            assert rows[0].image_items[0]["description"] == "完整图片描述"
            assert rows[0].raw_json["image_items"][0]["keep"] is False

            listed = await store.list_messages(platform_id="qq", chat_id="100")
            item = listed["items"][0]
            assert item["content"] == "[图片]"
            assert item["image_items"][0]["importance"] == 0.2
        finally:
            await store.close()

    run(scenario())


def test_update_message_edits_content_and_metadata(tmp_path):
    store = SQLiteContextStore(tmp_path)

    async def scenario():
        await store.start()
        await store.add_message_sync(base_message("m2", "old"))
        result = await store.update_message_record(
            {"platform_id": "qq", "chat_id": "100", "message_id": "m2", "role": "user"},
            {
                "content": "new content",
                "sender_name": "Bob",
                "image_status": "success",
                "image_descriptions": ["desc"],
            },
            reason="unit test",
        )
        assert result["updated_count"] == 1

        listed = await store.list_messages(platform_id="qq", chat_id="100")
        item = listed["items"][0]
        assert item["content"] == "new content"
        assert item["sender_name"] == "Bob"
        assert item["image_status"] == "success"
        assert item["image_descriptions"] == ["desc"]
        assert item["edited_at"] > 0
        assert item["edit_reason"] == "unit test"
        await store.close()

    run(scenario())


def test_update_by_id_respects_db_scope(tmp_path):
    store = SQLiteContextStore(tmp_path)

    async def scenario():
        await store.start()
        try:
            hot = base_message("same-id-hot", "hot old")
            cold = base_message("same-id-cold", "cold old")
            await store.add_message_sync(hot)
            cold_row = store._normalize_message(cold)
            with store._connection(store.cold_db_path) as conn:
                conn.execute(
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
                    cold_row,
                )
                conn.commit()

            hot_list = await store.list_messages(db_scope="hot")
            cold_list = await store.list_messages(db_scope="cold")
            assert hot_list["items"][0]["id"] == cold_list["items"][0]["id"] == 1

            result = await store.update_message_record(
                {"id": 1},
                {"content": "hot new"},
                reason="scope test",
                db_scope="hot",
            )
            assert result["updated_count"] == 1

            hot_after = await store.list_messages(db_scope="hot")
            cold_after = await store.list_messages(db_scope="cold")
            assert hot_after["items"][0]["content"] == "hot new"
            assert cold_after["items"][0]["content"] == "cold old"
        finally:
            await store.close()

    run(scenario())


def test_invalid_db_scope_is_rejected(tmp_path):
    store = SQLiteContextStore(tmp_path)

    async def scenario():
        await store.start()
        try:
            await store.add_message_sync(base_message("m3", "old"))
            try:
                await store.update_message_record(
                    {"id": 1},
                    {"content": "new"},
                    db_scope="typo",
                )
            except ValueError as exc:
                assert "db_scope" in str(exc)
            else:
                raise AssertionError("invalid db_scope should raise")
        finally:
            await store.close()

    run(scenario())

import asyncio
from types import SimpleNamespace

from test_decision_context_limits import ChatPlus

import sys


main_module = sys.modules["astrbot_plugin_group_chat_plus.main_under_test"]


class DummyEvent:
    def __init__(self, message):
        self.message_obj = SimpleNamespace(message=message)

    def get_platform_id(self):
        return "qq"

    def get_platform_name(self):
        return "aiocqhttp"

    def is_private_chat(self):
        return False

    def get_group_id(self):
        return "100"

    def get_sender_id(self):
        return "u2"


class FakeStore:
    def __init__(self, rows):
        self.rows = rows

    async def get_messages_by_ids(
        self, *, platform_id, chat_id, message_ids, include_cold=True
    ):
        assert platform_id == "qq"
        assert chat_id == "100"
        assert include_cold is True
        return {mid: self.rows[mid] for mid in message_ids if mid in self.rows}

    async def update_message_image_result(self, **kwargs):
        return None


def make_plugin():
    plugin = ChatPlus.__new__(ChatPlus)
    plugin.debug_mode = False
    plugin.enable_image_processing = True
    plugin.image_to_text_provider_id = "vision"
    plugin.image_to_text_timeout = 3
    plugin.image_description_cache = None
    plugin.context = SimpleNamespace(get_provider_by_id=lambda _provider_id: None)
    return plugin


def make_reply(message_id="quoted-1", message_str="[Image]"):
    reply = main_module.Reply()
    reply.id = message_id
    reply.message_str = message_str
    reply.chain = []
    reply.sender_id = "u1"
    reply.sender_nickname = "Alice"
    return reply


def run(coro):
    return asyncio.run(coro)


def test_enrich_quoted_image_from_sqlite(monkeypatch):
    async def scenario():
        plugin = make_plugin()
        reply = make_reply()
        event = DummyEvent([reply])
        row = SimpleNamespace(
            content="[图片]",
            image_descriptions=["一张猫趴在键盘上的图"],
            image_refs=["img-ref"],
            sender_id="u1",
            sender_name="Alice",
        )
        monkeypatch.setattr(
            main_module.ContextManager,
            "sqlite_store",
            FakeStore({"aiocqhttp_quoted-1": row}),
            raising=False,
        )

        text, reply_ids = await plugin._enrich_quoted_message_context(
            event, "[引用消息][At:3842578597]看看这个"
        )

        assert reply_ids == ["quoted-1"]
        assert "[引用 Alice(ID:u1): [图片内容: 一张猫趴在键盘上的图]]" in text
        assert "[At:3842578597]看看这个" in text

    run(scenario())


def test_enrich_quoted_image_from_remote_ref(monkeypatch):
    async def scenario():
        plugin = make_plugin()
        reply = make_reply("remote-1")
        event = DummyEvent([reply])
        monkeypatch.setattr(main_module.ContextManager, "sqlite_store", None, raising=False)

        async def fake_fetch_text(_event, _reply):
            return ""

        async def fake_fetch_images(_event, _reply=None):
            return ["remote-image-ref"]

        async def fake_describe(image_ref):
            assert image_ref == "remote-image-ref"
            return "一张远程引用图片"

        plugin._fetch_quoted_text = fake_fetch_text
        plugin._fetch_quoted_image_refs = fake_fetch_images
        plugin._describe_image_ref = fake_describe

        text, reply_ids = await plugin._enrich_quoted_message_context(
            event, "[引用消息]看看这个"
        )

        assert reply_ids == ["remote-1"]
        assert "[图片内容: 一张远程引用图片]" in text
        assert "看看这个" in text

    run(scenario())


def test_enrich_quoted_image_uses_clear_placeholder_when_unavailable(monkeypatch):
    async def scenario():
        plugin = make_plugin()
        reply = make_reply("missing-1")
        event = DummyEvent([reply])
        monkeypatch.setattr(main_module.ContextManager, "sqlite_store", None, raising=False)

        async def fake_fetch_text(_event, _reply):
            return ""

        async def fake_fetch_images(_event, _reply=None):
            return []

        plugin._fetch_quoted_text = fake_fetch_text
        plugin._fetch_quoted_image_refs = fake_fetch_images

        text, reply_ids = await plugin._enrich_quoted_message_context(
            event, "[引用消息]看看这个"
        )

        assert reply_ids == ["missing-1"]
        assert "[引用 Alice(ID:u1): 图片内容无法取得]" in text
        assert "看看这个" in text

    run(scenario())


def test_retry_quoted_pending_images_normalizes_reply_id(monkeypatch):
    class PendingStore:
        def __init__(self):
            self.updated = []
            self.succeeded = []

        async def get_pending_images_for_message(
            self, *, platform_id, chat_id, message_id
        ):
            assert platform_id == "qq"
            assert chat_id == "100"
            if message_id == "aiocqhttp_pending-1":
                return [
                    {"image_key": "k1", "image_ref": "remote-image-ref"},
                ]
            return []

        async def mark_image_succeeded(self, image_key, desc):
            self.succeeded.append((image_key, desc))

        async def update_message_image_result(self, **kwargs):
            self.updated.append(kwargs)

    async def scenario():
        plugin = make_plugin()
        reply = make_reply("pending-1", "[Image]")
        event = DummyEvent([reply])
        store = PendingStore()
        monkeypatch.setattr(main_module.ContextManager, "sqlite_store", store, raising=False)

        async def fake_fetch_images(_event, _reply=None):
            return ["remote-image-ref"]

        async def fake_describe(image_ref):
            assert image_ref == "remote-image-ref"
            return "待重试图片描述"

        plugin._fetch_quoted_image_refs = fake_fetch_images
        plugin._describe_image_ref = fake_describe

        await plugin._retry_quoted_pending_images(event)

        assert store.succeeded == [("k1", "待重试图片描述")]
        assert store.updated
        assert store.updated[0]["message_id"] == "aiocqhttp_pending-1"
        assert store.updated[0]["status"] == "success"

    run(scenario())


def test_enrich_quoted_message_no_reply_is_noop(monkeypatch):
    async def scenario():
        plugin = make_plugin()
        event = DummyEvent([])
        monkeypatch.setattr(main_module.ContextManager, "sqlite_store", None, raising=False)

        text, reply_ids = await plugin._enrich_quoted_message_context(event, "普通消息")

        assert text == "普通消息"
        assert reply_ids == []

    run(scenario())

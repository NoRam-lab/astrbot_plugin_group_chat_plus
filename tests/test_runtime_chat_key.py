import asyncio
from types import SimpleNamespace

from test_decision_context_limits import ChatPlus


class RuntimeKeyEvent:
    def __init__(
        self,
        *,
        platform_id="bot1",
        platform_name="aiocqhttp",
        group_id="588199994",
        raw_group_id=None,
        sender_id="10001",
        private=False,
        unified_msg_origin=None,
    ):
        self.platform_id = platform_id
        self.platform_name = platform_name
        self.group_id = group_id
        self.raw_group_id = raw_group_id
        self.sender_id = sender_id
        self.private = private
        self._extras = {}
        raw_message = {}
        if raw_group_id is not None:
            raw_message["group_id"] = raw_group_id
        self.message_obj = SimpleNamespace(
            group_id=group_id,
            raw_message=raw_message,
            message_id="msg-1",
            message=[],
            timestamp=123.0,
        )
        self._unified_msg_origin = unified_msg_origin or (
            f"{platform_id}:"
            f"{'FriendMessage' if private else 'GroupMessage'}:"
            f"{sender_id if private else (group_id or raw_group_id or 'unknown')}"
        )

    @property
    def unified_msg_origin(self):
        return self._unified_msg_origin

    def get_platform_id(self):
        return self.platform_id

    def get_platform_name(self):
        return self.platform_name

    def is_private_chat(self):
        return self.private

    def get_group_id(self):
        return self.group_id

    def get_sender_id(self):
        return self.sender_id

    def set_extra(self, key, value):
        self._extras[key] = value

    def get_extra(self, key, default=None):
        return self._extras.get(key, default)


class FakeWaitWindowBuffer:
    def __init__(self, keys=()):
        self._items = {key: [{"message_id": key}] for key in keys}
        self.cleared = []

    def chat_ids(self):
        return list(self._items.keys())

    def clear(self, key):
        self.cleared.append(key)
        return len(self._items.pop(key, []))


def make_plugin():
    plugin = ChatPlus.__new__(ChatPlus)
    plugin.debug_mode = False
    plugin.processing_sessions = {}
    plugin.enable_same_chat_parallel_reply = True
    plugin.wait_window_buffer = FakeWaitWindowBuffer()
    plugin._group_wait_windows = {}
    plugin._group_wait_window_lock = asyncio.Lock()
    plugin._group_wait_window_counter = 0
    plugin.group_wait_window_timeout_ms = 1
    plugin.group_wait_window_max_users = 5
    plugin._group_wait_window_max_extra = 3
    return plugin


def test_runtime_key_distinguishes_groups_when_chat_id_matches():
    plugin = make_plugin()
    event_a = RuntimeKeyEvent(group_id="811953586")
    event_b = RuntimeKeyEvent(group_id="588199994")

    key_a = plugin._get_runtime_chat_key(event_a, "aiocqhttp", False, "shared")
    key_b = plugin._get_runtime_chat_key(event_b, "aiocqhttp", False, "shared")

    assert key_a == "bot1:group:shared:811953586"
    assert key_b == "bot1:group:shared:588199994"
    assert key_a != key_b


def test_runtime_key_keeps_same_group_stable():
    plugin = make_plugin()
    event_a = RuntimeKeyEvent(group_id="588199994")
    event_b = RuntimeKeyEvent(group_id="588199994")

    key_a = plugin._get_runtime_chat_key(event_a, "aiocqhttp", False, "588199994")
    key_b = plugin._get_runtime_chat_key(event_b, "aiocqhttp", False, "588199994")

    assert key_a == key_b == "bot1:group:588199994:588199994"


def test_runtime_key_distinguishes_platform_instances():
    plugin = make_plugin()
    event_a = RuntimeKeyEvent(platform_id="bot1", group_id="588199994")
    event_b = RuntimeKeyEvent(platform_id="bot2", group_id="588199994")

    key_a = plugin._get_runtime_chat_key(event_a, "aiocqhttp", False, "588199994")
    key_b = plugin._get_runtime_chat_key(event_b, "aiocqhttp", False, "588199994")

    assert key_a == "bot1:group:588199994:588199994"
    assert key_b == "bot2:group:588199994:588199994"
    assert key_a != key_b


def test_runtime_key_uses_raw_group_id_fallback():
    plugin = make_plugin()
    event = RuntimeKeyEvent(group_id="", raw_group_id="811953586")

    key = plugin._get_runtime_chat_key(event, "aiocqhttp", False, "shared")

    assert key == "bot1:group:shared:811953586"


def test_processing_conflicts_are_scoped_by_runtime_key():
    plugin = make_plugin()
    plugin.processing_sessions = {"msg-a": "scope-a"}

    assert plugin._get_processing_conflicts("scope-b", "msg-b") == []
    assert plugin._get_processing_conflicts("scope-a", "msg-b") == ["msg-a"]
    assert plugin._get_processing_conflicts("scope-a", "msg-a") == []


def test_parallel_reply_mode_does_not_block_same_runtime_conflict():
    plugin = make_plugin()
    plugin.enable_same_chat_parallel_reply = True
    plugin.processing_sessions = {"msg-a": "scope-a"}

    assert plugin._get_processing_conflicts("scope-a", "msg-b") == ["msg-a"]
    assert plugin._get_blocking_processing_conflicts("scope-a", "msg-b") == []


def test_serial_reply_mode_blocks_same_runtime_conflict():
    plugin = make_plugin()
    plugin.enable_same_chat_parallel_reply = False
    plugin.processing_sessions = {"msg-a": "scope-a"}

    assert plugin._get_blocking_processing_conflicts("scope-a", "msg-b") == [
        "msg-a"
    ]


def test_wait_window_buffer_keys_are_per_root_message():
    plugin = make_plugin()

    key_a = plugin._make_wait_window_buffer_key(
        "scope-a", message_id="msg-a", window_token="token-a"
    )
    key_b = plugin._make_wait_window_buffer_key(
        "scope-a", message_id="msg-b", window_token="token-b"
    )

    assert key_a == "scope-a:window:token-a"
    assert key_b == "scope-a:window:token-b"
    assert key_a != key_b


def test_wait_window_cleanup_keys_include_only_runtime_window_buffers():
    plugin = make_plugin()
    plugin.wait_window_buffer = FakeWaitWindowBuffer(
        [
            "scope-a:window:token-a",
            "scope-a:window:token-b",
            "scope-b:window:token-c",
            "scope-aa:window:token-d",
        ]
    )

    cleanup_keys = plugin._get_wait_window_cleanup_keys({"scope-a"})

    assert cleanup_keys == {
        "scope-a",
        "scope-a:window:token-a",
        "scope-a:window:token-b",
    }


def test_wait_window_clear_only_current_root_buffer():
    plugin = make_plugin()
    plugin.wait_window_buffer = FakeWaitWindowBuffer(
        ["scope-a:window:token-a", "scope-a:window:token-b"]
    )
    event = RuntimeKeyEvent()
    event.set_extra(
        plugin._WAIT_WINDOW_BUFFER_KEY,
        "scope-a:window:token-a",
    )

    buffer_key, removed = plugin._clear_wait_window_buffer_for_event(
        event, "scope-a"
    )

    assert buffer_key == "scope-a:window:token-a"
    assert removed == 1
    assert plugin.wait_window_buffer.cleared == ["scope-a:window:token-a"]
    assert "scope-a:window:token-b" in plugin.wait_window_buffer.chat_ids()


def test_parallel_mode_does_not_absorb_wait_window_messages():
    async def run():
        plugin = make_plugin()
        plugin.enable_same_chat_parallel_reply = True
        plugin._group_wait_windows = {
            ("scope-a", "10001"): {"buffer_key": "scope-a:window:old"}
        }

        intercepted = await plugin._maybe_intercept_for_wait_window(
            RuntimeKeyEvent(sender_id="10001"),
            "588199994",
            "scope-a",
            False,
            False,
            None,
            "aiocqhttp",
        )

        assert intercepted is False

    asyncio.run(run())


def test_wait_window_state_key_is_per_message_in_parallel_mode():
    plugin = make_plugin()
    plugin.enable_same_chat_parallel_reply = True

    key_a = plugin._get_wait_window_state_key(
        "scope-a", "user-1", message_id="msg-a", buffer_key="buffer-a"
    )
    key_b = plugin._get_wait_window_state_key(
        "scope-a", "user-1", message_id="msg-b", buffer_key="buffer-b"
    )

    assert key_a == ("scope-a", "message:msg-a")
    assert key_b == ("scope-a", "message:msg-b")
    assert key_a != key_b


def test_wait_window_state_key_is_per_user_in_serial_mode():
    plugin = make_plugin()
    plugin.enable_same_chat_parallel_reply = False

    key_a = plugin._get_wait_window_state_key(
        "scope-a", "user-1", message_id="msg-a", buffer_key="buffer-a"
    )
    key_b = plugin._get_wait_window_state_key(
        "scope-a", "user-1", message_id="msg-b", buffer_key="buffer-b"
    )

    assert key_a == key_b == ("scope-a", "user-1")


def test_parallel_wait_windows_for_same_user_do_not_replace_each_other():
    async def run():
        plugin = make_plugin()
        plugin.enable_same_chat_parallel_reply = True
        plugin.group_wait_window_timeout_ms = 20

        task_a = asyncio.create_task(
            plugin._run_group_wait_window(
                "588199994",
                "scope-a",
                "user-1",
                "scope-a:window:token-a",
                message_id="msg-a",
            )
        )
        task_b = asyncio.create_task(
            plugin._run_group_wait_window(
                "588199994",
                "scope-a",
                "user-1",
                "scope-a:window:token-b",
                message_id="msg-b",
            )
        )

        await asyncio.sleep(0)

        assert set(plugin._group_wait_windows) == {
            ("scope-a", "message:msg-a"),
            ("scope-a", "message:msg-b"),
        }

        await asyncio.gather(task_a, task_b)

    asyncio.run(run())

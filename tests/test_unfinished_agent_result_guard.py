import asyncio
from types import SimpleNamespace

from test_decision_context_limits import ChatPlus


class FakeResult:
    def __init__(self, *, is_llm=True, chain=None):
        self._is_llm = is_llm
        self.chain = chain if chain is not None else [SimpleNamespace(text="draft")]

    def is_llm_result(self):
        return self._is_llm


class FakeEvent:
    def __init__(self, result, message_id="msg-1"):
        self._result = result
        self.clear_count = 0
        self.message_obj = SimpleNamespace(message_id=message_id)
        self.call_llm = False

    def get_platform_name(self):
        return "aiocqhttp"

    def get_platform_id(self):
        return "bot1"

    def is_private_chat(self):
        return False

    def get_group_id(self):
        return "group-1"

    def get_sender_id(self):
        return "user-1"

    def get_result(self):
        return self._result

    def clear_result(self):
        self.clear_count += 1
        self._result = None


def run(coro):
    return asyncio.run(coro)


def make_plugin(*, enabled=True, processing=True, done=False):
    plugin = ChatPlus.__new__(ChatPlus)
    plugin.debug_mode = False
    plugin.suppress_unfinished_agent_llm_results = enabled
    message_id = "aiocqhttp_msg-1"
    plugin.processing_sessions = {message_id: "group-1"} if processing else {}
    plugin._agent_done_flags = {message_id} if done else set()
    plugin._pending_bot_replies = {}
    plugin.raw_reply_cache = {}
    plugin.recent_replies_cache = {}
    plugin.enable_duplicate_filter = False
    plugin.enable_duplicate_time_limit = False
    plugin.duplicate_filter_time_limit = 60
    plugin.duplicate_filter_check_count = 5
    plugin._DUPLICATE_CACHE_SIZE_LIMIT = 100
    plugin.content_filter = SimpleNamespace(
        process_for_output=lambda text: text,
        process_for_save=lambda text: text,
    )
    plugin.typing_simulator_enabled = False
    plugin.typing_simulator = None
    plugin._active_reply_flows = {}
    plugin._superseded_reply_message_ids = set()
    plugin._superseded_reply_flow_times = {}
    return plugin


def test_guard_clears_unfinished_llm_result_for_processing_session():
    plugin = make_plugin()
    event = FakeEvent(FakeResult())

    run(plugin.suppress_unfinished_agent_llm_result_guard(event))

    assert event.get_result() is None
    assert event.clear_count == 1
    assert plugin._pending_bot_replies == {}
    assert plugin.raw_reply_cache == {}


def test_guard_allows_completed_agent_result():
    plugin = make_plugin(done=True)
    result = FakeResult()
    event = FakeEvent(result)

    run(plugin.suppress_unfinished_agent_llm_result_guard(event))

    assert event.get_result() is result
    assert event.clear_count == 0


def test_guard_ignores_non_processing_session():
    plugin = make_plugin(processing=False)
    result = FakeResult()
    event = FakeEvent(result)

    run(plugin.suppress_unfinished_agent_llm_result_guard(event))

    assert event.get_result() is result
    assert event.clear_count == 0


def test_guard_ignores_non_llm_result():
    plugin = make_plugin()
    result = FakeResult(is_llm=False)
    event = FakeEvent(result)

    run(plugin.suppress_unfinished_agent_llm_result_guard(event))

    assert event.get_result() is result
    assert event.clear_count == 0


def test_guard_can_be_disabled():
    plugin = make_plugin(enabled=False)
    result = FakeResult()
    event = FakeEvent(result)

    run(plugin.suppress_unfinished_agent_llm_result_guard(event))

    assert event.get_result() is result
    assert event.clear_count == 0


def test_guard_clears_unfinished_llm_result_even_after_image_decoration():
    plugin = make_plugin()
    event = FakeEvent(FakeResult(chain=[SimpleNamespace(url="file://reply.png")]))

    run(plugin.suppress_unfinished_agent_llm_result_guard(event))

    assert event.get_result() is None
    assert event.clear_count == 1


def test_decorating_result_clears_superseded_reply():
    message_id = "aiocqhttp_msg-1"
    plugin = make_plugin(processing=True, done=True)
    plugin._superseded_reply_message_ids.add(message_id)
    plugin._superseded_reply_flow_times[message_id] = 123.0
    plugin._active_reply_flows[message_id] = {
        "runtime_chat_key": "bot1:group:group-1:group-1",
        "stage": "reply_generate",
    }
    event = FakeEvent(FakeResult())

    run(plugin.on_decorating_result(event))

    assert event.get_result() is None
    assert event.clear_count == 1
    assert plugin.raw_reply_cache == {}
    assert plugin._pending_bot_replies == {}
    assert message_id not in plugin._active_reply_flows

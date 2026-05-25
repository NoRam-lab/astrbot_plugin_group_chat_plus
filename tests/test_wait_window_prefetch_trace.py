import asyncio
import sys
from types import SimpleNamespace

from test_decision_context_limits import ChatPlus


main_module = sys.modules["astrbot_plugin_group_chat_plus.main_under_test"]


class DummyEvent:
    def __init__(self, message_id="m1"):
        self.extra = {}
        self.message_obj = SimpleNamespace(message_id=message_id)

    def get_extra(self, key, default=None):
        return self.extra.get(key, default)

    def set_extra(self, key, value):
        self.extra[key] = value

    def get_sender_id(self):
        return "u1"

    def get_platform_name(self):
        return "test"


def make_plugin():
    plugin = ChatPlus.__new__(ChatPlus)
    plugin.context = object()
    plugin.debug_mode = False
    plugin.enable_performance_timing_log = False
    plugin.group_wait_window_prefetch_memory = True
    plugin.enable_memory_injection = True
    plugin.memory_insertion_timing = "post_decision"
    plugin.memory_plugin_mode = "livingmemory"
    plugin.livingmemory_top_k = 3
    plugin.livingmemory_version = "v1"
    plugin.background_task_warning_threshold = 5.0
    plugin._background_tasks = set()
    return plugin


def install_memory(monkeypatch, get_memories):
    monkeypatch.setattr(
        main_module.MemoryInjector,
        "check_memory_plugin_available",
        staticmethod(lambda *args, **kwargs: True),
        raising=False,
    )
    monkeypatch.setattr(
        main_module.MemoryInjector,
        "get_memories",
        staticmethod(get_memories),
        raising=False,
    )


def test_prefetch_result_is_reused_once_per_window(monkeypatch):
    async def run():
        calls = []

        async def fake_get_memories(*args, **kwargs):
            calls.append(kwargs.get("mode"))
            return "memory text"

        install_memory(monkeypatch, fake_get_memories)
        plugin = make_plugin()
        event = DummyEvent()
        trace = plugin._build_message_trace(event, "chat1")
        plugin._set_message_trace(event, trace)

        task = plugin._start_memory_prefetch_task(event)
        assert task is plugin._start_memory_prefetch_task(event)

        first = await plugin._get_memories_with_prefetch(event, task, "decision")
        second = await plugin._get_memories_with_prefetch(event, task, "reply")

        assert first == "memory text"
        assert second == "memory text"
        assert calls == ["livingmemory"]
        assert event.get_extra(plugin._WAIT_WINDOW_PREFETCH_RESULT_KEY) == "memory text"

    asyncio.run(run())


def test_prefetch_failure_falls_back_once_and_reuses_result(monkeypatch):
    async def run():
        calls = 0

        async def fake_get_memories(*args, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 1:
                raise RuntimeError("prefetch failed")
            return "fallback memory"

        install_memory(monkeypatch, fake_get_memories)
        plugin = make_plugin()
        event = DummyEvent()
        trace = plugin._build_message_trace(event, "chat1")
        plugin._set_message_trace(event, trace)

        task = plugin._start_memory_prefetch_task(event)
        first = await plugin._get_memories_with_prefetch(event, task, "decision")
        second = await plugin._get_memories_with_prefetch(event, task, "reply")

        assert first == "fallback memory"
        assert second == "fallback memory"
        assert calls == 2
        assert event.get_extra(plugin._WAIT_WINDOW_PREFETCH_RESULT_KEY) == "fallback memory"

    asyncio.run(run())


def test_cancelled_prefetch_falls_back_once(monkeypatch):
    async def run():
        calls = 0

        async def fake_get_memories(*args, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 1:
                await asyncio.sleep(10)
            return "fallback after cancel"

        install_memory(monkeypatch, fake_get_memories)
        plugin = make_plugin()
        event = DummyEvent()
        trace = plugin._build_message_trace(event, "chat1")
        plugin._set_message_trace(event, trace)

        task = plugin._start_memory_prefetch_task(event)
        await asyncio.sleep(0)
        task.cancel()

        first = await plugin._get_memories_with_prefetch(event, task, "decision")
        second = await plugin._get_memories_with_prefetch(event, task, "reply")

        assert first == "fallback after cancel"
        assert second == "fallback after cancel"
        assert calls == 2

    asyncio.run(run())


def test_trace_helper_records_stable_stage_sequence():
    plugin = make_plugin()
    event = DummyEvent()

    trace = plugin._build_message_trace(event, "chat1")
    plugin._set_message_trace(event, trace)
    plugin._trace_step(trace, "initial_checks", trace["started_at"], detail="ok")
    plugin._trace_step(trace, "ai_decision", trace["started_at"], detail="yes")
    plugin._trace_summary(trace)

    assert [step[0] for step in trace["steps"]] == [
        "initial_checks",
        "ai_decision",
    ]
    assert plugin._get_message_trace(event) is trace

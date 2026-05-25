import asyncio
import importlib.util
import sys
import types
from pathlib import Path


def load_chatplus_class():
    root = Path(__file__).resolve().parents[1]
    package = types.ModuleType("astrbot_plugin_group_chat_plus")
    package.__path__ = [str(root)]
    sys.modules.setdefault("astrbot_plugin_group_chat_plus", package)

    api_all = types.ModuleType("astrbot.api.all")

    class Star:
        def __init__(self, context=None):
            self.context = context

    def register(*args, **kwargs):
        def decorator(cls):
            return cls

        return decorator

    api_all.Star = Star
    api_all.Context = object
    api_all.AstrBotConfig = dict
    api_all.AstrMessageEvent = object
    api_all.AstrBotMessage = type("AstrBotMessage", (), {})
    api_all.MessageMember = type("MessageMember", (), {})
    api_all.MessageType = types.SimpleNamespace(
        GROUP_MESSAGE="group", FRIEND_MESSAGE="friend"
    )
    api_all.register = register
    api_all.event_message_type = lambda *args, **kwargs: (lambda fn: fn)
    api_all.EventMessageType = types.SimpleNamespace(GROUP_MESSAGE="group", ALL="all")

    api_module = types.ModuleType("astrbot.api")
    api_module.logger = types.SimpleNamespace(
        info=lambda *args, **kwargs: None,
        warning=lambda *args, **kwargs: None,
        error=lambda *args, **kwargs: None,
        debug=lambda *args, **kwargs: None,
    )

    filter_module = types.ModuleType("astrbot.api.event.filter")
    filter_module.command = lambda *args, **kwargs: (lambda fn: fn)
    filter_module.on_platform_loaded = lambda *args, **kwargs: (lambda fn: fn)
    filter_module.on_llm_request = lambda *args, **kwargs: (lambda fn: fn)
    filter_module.on_llm_response = lambda *args, **kwargs: (lambda fn: fn)
    filter_module.on_decorating_result = lambda *args, **kwargs: (lambda fn: fn)
    filter_module.after_message_sent = lambda *args, **kwargs: (lambda fn: fn)
    filter_module.event_message_type = lambda *args, **kwargs: (lambda fn: fn)
    filter_module.EventMessageType = types.SimpleNamespace(ALL="all")

    event_module = types.ModuleType("astrbot.api.event")
    event_module.filter = filter_module
    event_module.event_message_type = filter_module.event_message_type
    event_module.EventMessageType = types.SimpleNamespace(
        GROUP_MESSAGE="group", ALL="all"
    )

    components_module = types.ModuleType("astrbot.core.message.components")
    for name in (
        "Plain",
        "Poke",
        "At",
        "AtAll",
        "Forward",
        "Image",
        "Reply",
        "Json",
        "Video",
        "File",
    ):
        setattr(components_module, name, type(name, (), {}))

    result_module = types.ModuleType("astrbot.core.message.message_event_result")
    result_module.MessageChain = type("MessageChain", (), {})

    provider_entities = types.ModuleType("astrbot.core.provider.entities")
    provider_entities.ProviderRequest = type("ProviderRequest", (), {})

    star_tools = types.ModuleType("astrbot.core.star.star_tools")
    star_tools.StarTools = types.SimpleNamespace(get_data_dir=lambda: root)

    aiocq_event = types.ModuleType(
        "astrbot.core.platform.sources.aiocqhttp.aiocqhttp_message_event"
    )
    aiocq_event.AiocqhttpMessageEvent = type("AiocqhttpMessageEvent", (), {})
    aiocq_adapter = types.ModuleType(
        "astrbot.core.platform.sources.aiocqhttp.aiocqhttp_platform_adapter"
    )
    aiocq_adapter.AiocqhttpAdapter = type("AiocqhttpAdapter", (), {})

    sys.modules["astrbot.api"] = api_module
    sys.modules["astrbot.api.all"] = api_all
    sys.modules["astrbot.api.event"] = event_module
    sys.modules["astrbot.api.event.filter"] = filter_module
    sys.modules["astrbot.core.message.components"] = components_module
    sys.modules["astrbot.core.message.message_event_result"] = result_module
    sys.modules["astrbot.core.provider.entities"] = provider_entities
    sys.modules["astrbot.core.star.star_tools"] = star_tools
    sys.modules[
        "astrbot.core.platform.sources.aiocqhttp.aiocqhttp_message_event"
    ] = aiocq_event
    sys.modules[
        "astrbot.core.platform.sources.aiocqhttp.aiocqhttp_platform_adapter"
    ] = aiocq_adapter

    utils_module = types.ModuleType("astrbot_plugin_group_chat_plus.utils")
    for name in (
        "ProbabilityManager",
        "MessageProcessor",
        "ImageHandler",
        "ContextManager",
        "DecisionAI",
        "ReplyHandler",
        "MemoryInjector",
        "ToolsReminder",
        "KeywordChecker",
        "MessageCleaner",
        "AttentionManager",
        "MoodTracker",
        "FrequencyAdjuster",
        "TypingSimulator",
        "TimePeriodManager",
        "HumanizeModeManager",
        "CooldownManager",
        "PlatformLTMHelper",
        "RuntimeMessageSnapshotStore",
        "WaitWindowBuffer",
        "EmojiDetector",
        "ForwardMessageParser",
        "WelcomeMessageParser",
        "ReplyDensityManager",
        "GlobalTimeControlManager",
        "ImageImportancePolicy",
        "ImageSpamGate",
    ):
        setattr(utils_module, name, type(name, (), {}))
    utils_module.EMOJI_MARKER = "[表情包图片]"
    sys.modules["astrbot_plugin_group_chat_plus.utils"] = utils_module

    image_cache_module = types.ModuleType(
        "astrbot_plugin_group_chat_plus.utils.image_description_cache"
    )
    image_cache_module.ImageDescriptionCache = type("ImageDescriptionCache", (), {})
    sys.modules[
        "astrbot_plugin_group_chat_plus.utils.image_description_cache"
    ] = image_cache_module

    class FakeImageImportancePolicy:
        @classmethod
        def from_config(cls, _config):
            return cls()

    utils_module.ImageImportancePolicy = FakeImageImportancePolicy

    image_policy_module = types.ModuleType(
        "astrbot_plugin_group_chat_plus.utils.image_importance_policy"
    )
    image_policy_module.ImageImportancePolicy = FakeImageImportancePolicy
    sys.modules[
        "astrbot_plugin_group_chat_plus.utils.image_importance_policy"
    ] = image_policy_module

    content_filter_module = types.ModuleType(
        "astrbot_plugin_group_chat_plus.utils.content_filter"
    )
    content_filter_module.ContentFilterManager = type("ContentFilterManager", (), {})
    sys.modules[
        "astrbot_plugin_group_chat_plus.utils.content_filter"
    ] = content_filter_module

    path = root / "main.py"
    spec = importlib.util.spec_from_file_location(
        "astrbot_plugin_group_chat_plus.main_under_test",
        path,
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.ChatPlus


ChatPlus = load_chatplus_class()
main_module = sys.modules["astrbot_plugin_group_chat_plus.main_under_test"]


class DummyEvent:
    def __init__(self, sender_id="10001", content="hello"):
        self.sender_id = sender_id
        self.content = content
        self.message_obj = types.SimpleNamespace(
            message=[],
            message_id="msg-1",
            timestamp=123.0,
        )
        self._extra = {}

    def is_private_chat(self):
        return False

    def get_group_id(self):
        return "group-1"

    def get_sender_id(self):
        return self.sender_id

    def get_sender_name(self):
        return "Alice"

    def get_platform_name(self):
        return "aiocqhttp"

    def get_platform_id(self):
        return "qq"

    def get_self_id(self):
        return "bot-1"

    def get_message_outline(self):
        return self.content

    def get_message_str(self):
        return self.content

    def set_extra(self, key, value):
        self._extra[key] = value

    def get_extra(self, key, default=None):
        return self._extra.get(key, default)


def run(coro):
    return asyncio.run(coro)


def test_merge_context_fetch_limit_uses_larger_positive():
    assert ChatPlus._merge_context_fetch_limit(80, 3) == 80
    assert ChatPlus._merge_context_fetch_limit(0, 30) == 30
    assert ChatPlus._merge_context_fetch_limit(0, 0) == 0


def test_merge_context_fetch_limit_preserves_unlimited():
    assert ChatPlus._merge_context_fetch_limit(-1, 30) == -1
    assert ChatPlus._merge_context_fetch_limit(80, -1) == -1


def test_slice_history_for_context_limits_recent_items():
    history = list(range(10))
    assert ChatPlus._slice_history_for_context(history, 3) == [7, 8, 9]
    assert ChatPlus._slice_history_for_context(history, 0) == []
    assert ChatPlus._slice_history_for_context(history, -1) == history


def test_normalize_context_limit_handles_invalid_values():
    assert ChatPlus._normalize_context_limit("3", 30, "x") == 3
    assert ChatPlus._normalize_context_limit("bad", 30, "x") == 30
    assert ChatPlus._normalize_context_limit(-5, 30, "x") == -1


def test_active_image_blacklist_matches_string_and_numeric_ids_independently():
    plugin = ChatPlus.__new__(ChatPlus)
    plugin.debug_mode = False
    plugin.active_image_understanding_blacklist_user_ids = (
        ChatPlus._normalize_user_id_set(["10001", 20002])
    )
    plugin.enable_user_blacklist = False
    plugin.blacklist_user_ids = ["10001"]

    string_event = types.SimpleNamespace(get_sender_id=lambda: "10001")
    numeric_event = types.SimpleNamespace(get_sender_id=lambda: 20002)
    other_event = types.SimpleNamespace(get_sender_id=lambda: "30003")

    assert plugin._is_active_image_understanding_blacklisted(string_event) is True
    assert plugin._is_active_image_understanding_blacklisted(numeric_event) is True
    assert plugin._is_active_image_understanding_blacklisted(other_event) is False
    assert plugin._is_user_blacklisted(string_event) is False


def test_read_air_blacklist_matches_and_only_applies_to_plain_messages():
    plugin = ChatPlus.__new__(ChatPlus)
    plugin.read_air_blacklist_user_ids = ChatPlus._normalize_user_id_set(
        ["10001", 20002]
    )
    string_event = DummyEvent(sender_id="10001")
    numeric_event = DummyEvent(sender_id=20002)
    other_event = DummyEvent(sender_id="30003")

    assert plugin._is_read_air_blacklisted(string_event) is True
    assert plugin._is_read_air_blacklisted(numeric_event) is True
    assert plugin._is_read_air_blacklisted(other_event) is False
    assert plugin._should_apply_read_air_blacklist(
        string_event,
        is_at_message=False,
        has_trigger_keyword=False,
        is_reply_to_bot=False,
    ) is True
    assert plugin._should_apply_read_air_blacklist(
        string_event,
        is_at_message=True,
        has_trigger_keyword=False,
        is_reply_to_bot=False,
    ) is False
    assert plugin._should_apply_read_air_blacklist(
        string_event,
        is_at_message=False,
        has_trigger_keyword=True,
        is_reply_to_bot=False,
    ) is False


def test_record_filtered_user_message_uses_source_and_probability_flag(monkeypatch):
    async def scenario():
        plugin = ChatPlus.__new__(ChatPlus)
        plugin.debug_mode = False
        plugin._get_message_id = lambda _event: "filtered-1"
        event = DummyEvent(content="/help")
        saved = []

        monkeypatch.setattr(
            main_module.MessageCleaner,
            "extract_raw_message_from_event",
            staticmethod(lambda _event: "/help"),
            raising=False,
        )

        async def fake_save(_event, cached_message, *, source=""):
            saved.append((cached_message, source))
            return True

        monkeypatch.setattr(
            main_module.ContextManager,
            "save_cached_user_message",
            fake_save,
            raising=False,
        )

        ok = await plugin._record_filtered_user_message(
            event, source="command_filtered"
        )

        assert ok is True
        assert saved[0][1] == "command_filtered"
        assert saved[0][0]["content"] == "/help"
        assert saved[0][0]["probability_filtered"] is True
        assert saved[0][0]["image_refs"] == []

    run(scenario())


def test_command_filter_records_only_when_enabled():
    async def scenario(record_enabled):
        plugin = ChatPlus.__new__(ChatPlus)
        plugin.debug_mode = False
        plugin.enable_group_chat = True
        plugin.record_filtered_command_messages = record_enabled
        plugin.command_messages = {}
        plugin._is_enabled = lambda _event: True
        plugin._is_command_message = lambda _event: True
        plugin._get_message_id = lambda _event: "cmd-1"
        recorded = []

        async def fake_record(_event, *, source):
            recorded.append(source)
            return True

        plugin._record_filtered_user_message = fake_record
        await plugin.command_filter_handler(DummyEvent(content="/help"))
        return recorded, plugin.command_messages

    recorded_off, commands_off = run(scenario(False))
    recorded_on, commands_on = run(scenario(True))

    assert recorded_off == []
    assert "cmd-1" in commands_off
    assert recorded_on == ["command_filtered"]
    assert "cmd-1" in commands_on


def test_blacklist_keyword_recording_is_separately_switchable(monkeypatch):
    async def scenario(record_enabled):
        plugin = ChatPlus.__new__(ChatPlus)
        plugin.debug_mode = False
        plugin.blacklist_keywords = ["blocked"]
        plugin.record_blacklist_keyword_messages = record_enabled
        plugin._is_enabled = lambda _event: True
        recorded = []

        async def fake_record(_event, *, source):
            recorded.append(source)
            return True

        plugin._record_filtered_user_message = fake_record
        monkeypatch.setattr(
            main_module.MessageProcessor,
            "is_message_from_bot",
            staticmethod(lambda _event: False),
            raising=False,
        )
        monkeypatch.setattr(
            main_module.KeywordChecker,
            "check_blacklist_keywords",
            staticmethod(lambda _event, _keywords: True),
            raising=False,
        )

        result = await plugin._perform_initial_checks(DummyEvent(content="blocked"))
        return recorded, result

    recorded_off, result_off = run(scenario(False))
    recorded_on, result_on = run(scenario(True))

    assert recorded_off == []
    assert result_off[0] is False
    assert recorded_on == ["blacklist_keyword_filtered"]
    assert result_on[0] is False


def test_process_message_read_air_blacklist_records_and_returns_before_probability():
    async def scenario():
        plugin = ChatPlus.__new__(ChatPlus)
        plugin.debug_mode = False
        plugin.enable_performance_timing_log = False
        plugin.frequency_adjuster_enabled = False
        plugin.frequency_adjuster = None
        plugin.read_air_blacklist_user_ids = ChatPlus._normalize_user_id_set(["10001"])
        plugin._get_message_id = lambda _event: "air-1"

        async def fake_initial(_event):
            return True, "aiocqhttp", False, "group-1"

        async def fake_triggers(_event):
            return False, False, ""

        plugin._perform_initial_checks = fake_initial
        plugin._check_message_triggers = fake_triggers
        plugin._is_reply_to_bot_message = lambda _event: False
        plugin._check_poke_message = lambda _event: {
            "is_poke": False,
            "should_ignore": False,
        }
        recorded = []

        async def fake_record(_event, *, source):
            recorded.append(source)
            return True

        plugin._record_filtered_user_message = fake_record
        plugin._check_probability_before_processing = lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("probability should not run")
        )

        event = DummyEvent(sender_id="10001", content="normal")
        async for _ in plugin._process_message(event):
            pass

        assert recorded == ["read_air_blacklisted"]

    run(scenario())

import asyncio
import importlib.util
import sys
import types
from pathlib import Path


def load_reply_handlers():
    root = Path(__file__).resolve().parents[1]
    package = types.ModuleType("astrbot_plugin_group_chat_plus")
    package.__path__ = [str(root)]
    utils_package = types.ModuleType("astrbot_plugin_group_chat_plus.utils")
    utils_package.__path__ = [str(root / "utils")]
    sys.modules.setdefault("astrbot_plugin_group_chat_plus", package)
    sys.modules.setdefault("astrbot_plugin_group_chat_plus.utils", utils_package)

    api_all = types.ModuleType("astrbot.api.all")
    api_all.Context = object
    api_all.MessageEventResult = type("MessageEventResult", (), {})
    api_all.EventResultType = types.SimpleNamespace(STOP="stop")
    api_all.ResultContentType = types.SimpleNamespace(
        STREAMING_RESULT="streaming_result",
        STREAMING_FINISH="streaming_finish",
    )
    api_all.logger = types.SimpleNamespace(
        info=lambda *args, **kwargs: None,
        warning=lambda *args, **kwargs: None,
        error=lambda *args, **kwargs: None,
        debug=lambda *args, **kwargs: None,
        level=20,
    )

    event_module = types.ModuleType("astrbot.api.event")
    event_module.AstrMessageEvent = object

    provider_entities = types.ModuleType("astrbot.core.provider.entities")
    provider_entities.ProviderRequest = type("ProviderRequest", (), {})

    sys.modules["astrbot.api.all"] = api_all
    sys.modules["astrbot.api.event"] = event_module
    sys.modules["astrbot.core.provider.entities"] = provider_entities

    reply_handler_path = root / "utils" / "reply_handler.py"
    reply_spec = importlib.util.spec_from_file_location(
        "astrbot_plugin_group_chat_plus.utils.reply_handler",
        reply_handler_path,
    )
    reply_module = importlib.util.module_from_spec(reply_spec)
    sys.modules[reply_spec.name] = reply_module
    reply_spec.loader.exec_module(reply_module)

    dkq_path = root / "utils" / "reply_handler_dkq.py"
    dkq_spec = importlib.util.spec_from_file_location(
        "astrbot_plugin_group_chat_plus.utils.reply_handler_dkq",
        dkq_path,
    )
    dkq_module = importlib.util.module_from_spec(dkq_spec)
    sys.modules[dkq_spec.name] = dkq_module
    dkq_spec.loader.exec_module(dkq_module)
    return reply_module.ReplyHandler, dkq_module.ReplyHandlerDKQ


ReplyHandler, ReplyHandlerDKQ = load_reply_handlers()
reply_module = sys.modules["astrbot_plugin_group_chat_plus.utils.reply_handler"]


class FakeToolSet:
    def __init__(self):
        self.tools = [
            types.SimpleNamespace(name="active_tool", active=True),
            types.SimpleNamespace(name="inactive_tool", active=False),
        ]

    def remove_tool(self, name):
        self.tools = [tool for tool in self.tools if tool.name != name]


class FakeToolManager:
    def __init__(self):
        self.tool_set = FakeToolSet()

    def get_full_tool_set(self):
        return self.tool_set


class FakePersonaManager:
    async def get_default_persona_v3(self, unified_msg_origin):
        return {
            "prompt": "persona prompt",
            "_begin_dialogs_processed": [
                {"role": "user", "content": "preset user"},
                {"role": "assistant", "content": "preset assistant"},
            ],
        }


class FakeContext:
    def __init__(self):
        self.tool_manager = FakeToolManager()
        self.persona_manager = FakePersonaManager()

    def get_llm_tool_manager(self):
        return self.tool_manager


class FakeEvent:
    session_id = "session-1"
    unified_msg_origin = "origin-1"

    def __init__(self):
        self.extras = {}
        self.request_kwargs = None

    def get_sender_id(self):
        return "10001"

    def get_sender_name(self):
        return "Alice"

    def get_message_str(self):
        return "今天群里好安静"

    def set_extra(self, key, value):
        self.extras[key] = value

    def request_llm(self, **kwargs):
        self.request_kwargs = kwargs
        return types.SimpleNamespace(kind="provider_request")

    def plain_result(self, text):
        return types.SimpleNamespace(kind="plain_result", text=text)


def test_dkq_prompt_marks_read_air_group_chat_scene():
    prompt = ReplyHandlerDKQ.SYSTEM_REPLY_PROMPT

    assert "读空气插话场景" in prompt
    assert "不是别人直接发给你的私聊式提问" in prompt
    assert "群友在群里和其他群友说话" in prompt
    assert "自然插一句" in prompt
    assert "我看到你在跟我说" in prompt


def test_dkq_sender_emphasis_does_not_treat_sender_as_dialog_target():
    text = ReplyHandlerDKQ._build_sender_emphasis("10001", "Alice", True)

    assert "[系统信息-当前群聊发言者]" in text
    assert "不代表 ta 在直接找你或向你提问" in text
    assert "像群友一样自然接话" in text
    assert "[系统信息-当前对话对象]" not in text


def test_normal_reply_handler_keeps_direct_dialog_sender_emphasis():
    text = ReplyHandler._build_sender_emphasis("10001", "Alice", True)

    assert "[系统信息-当前对话对象]" in text
    assert "只回复 Alice 的当前消息" in text


def test_dkq_generate_reply_inherits_request_flow_and_uses_dkq_prompt():
    event = FakeEvent()
    context = FakeContext()
    image_urls = ["https://example.test/image.png"]

    result = asyncio.run(
        ReplyHandlerDKQ.generate_reply(
            event,
            context,
            "【当前新消息】Alice: 今天群里好安静",
            "",
            image_urls=image_urls,
        )
    )

    assert result.kind == "provider_request"
    assert event.extras[reply_module.PLUGIN_REQUEST_MARKER] is True
    assert event.extras[reply_module.PLUGIN_CUSTOM_CONTEXTS] == []
    assert event.extras[reply_module.PLUGIN_CUSTOM_SYSTEM_PROMPT] == "persona prompt"
    assert event.extras[reply_module.PLUGIN_IMAGE_URLS] == image_urls
    assert event.extras[reply_module.PLUGIN_FUNC_TOOL] is context.tool_manager.tool_set
    assert [tool.name for tool in context.tool_manager.tool_set.tools] == ["active_tool"]
    assert event.extras[reply_module.PLUGIN_CURRENT_MESSAGE] == "今天群里好安静"
    assert event.request_kwargs["prompt"] == "今天群里好安静"
    assert event.request_kwargs["func_tool_manager"] is context.tool_manager
    assert event.request_kwargs["image_urls"] == image_urls
    assert event.request_kwargs["contexts"] == []
    assert event.request_kwargs["system_prompt"] == "persona prompt"

    full_prompt = event.extras[reply_module.PLUGIN_CUSTOM_PROMPT]
    assert "=== 预设对话 ===" in full_prompt
    assert "读空气插话场景" in full_prompt
    assert "[系统信息-当前群聊发言者] Alice" in full_prompt
    assert "不代表 ta 在直接找你或向你提问" in full_prompt
    assert "[系统信息-当前对话对象]" not in full_prompt

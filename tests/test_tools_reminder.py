import importlib.util
import sys
import types
from pathlib import Path
from types import SimpleNamespace


class DummyLogger:
    def info(self, *args, **kwargs):
        pass

    def warning(self, *args, **kwargs):
        pass

    def error(self, *args, **kwargs):
        pass


astrbot_module = types.ModuleType("astrbot")
astrbot_api_module = types.ModuleType("astrbot.api")
astrbot_api_all_module = types.ModuleType("astrbot.api.all")
astrbot_api_all_module.Context = object
astrbot_api_all_module.logger = DummyLogger()
sys.modules.setdefault("astrbot", astrbot_module)
sys.modules.setdefault("astrbot.api", astrbot_api_module)
sys.modules.setdefault("astrbot.api.all", astrbot_api_all_module)

tools_reminder_path = (
    Path(__file__).resolve().parents[1] / "utils" / "tools_reminder.py"
)
spec = importlib.util.spec_from_file_location("tools_reminder_under_test", tools_reminder_path)
tools_reminder_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tools_reminder_module)
ToolsReminder = tools_reminder_module.ToolsReminder


class DummyToolSet:
    def __init__(self, tools):
        self.tools = tools


def make_tool(name, active=True, description="desc", parameters=None):
    return SimpleNamespace(
        name=name,
        active=active,
        description=description,
        parameters=parameters or {"type": "object", "properties": {}},
    )


def test_get_available_tools_from_source_filters_inactive_and_deduplicates():
    tools = DummyToolSet(
        [
            make_tool("web_search", active=False, description="disabled"),
            make_tool("web_search", active=True, description="enabled"),
            make_tool("image_generate", active=True),
        ]
    )

    result = ToolsReminder.get_available_tools_from_source(tools)

    assert [tool["name"] for tool in result] == ["web_search", "image_generate"]
    assert result[0]["description"] == "enabled"


def test_get_available_tools_from_source_extracts_parameters():
    tools = [
        make_tool(
            "weather",
            parameters={
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "城市名称",
                    }
                },
            },
        )
    ]

    result = ToolsReminder.get_available_tools_from_source(tools)

    assert result[0]["parameters"] == [
        {"name": "city", "type": "string", "description": "城市名称"}
    ]


def test_inject_tools_to_message_uses_final_tool_source_and_skips_empty_context():
    injected = ToolsReminder.inject_tools_to_message(
        "原始消息",
        context=None,
        tool_source=[
            make_tool("plugin_tool", active=True),
            make_tool("blocked_tool", active=False),
            make_tool("web_search_tavily", active=True),
        ],
    )

    assert "=== 可用工具列表 ===" in injected
    assert "plugin_tool" in injected
    assert "web_search_tavily" in injected
    assert "blocked_tool" not in injected


def test_inject_tools_to_message_does_not_duplicate_existing_reminder():
    message = "原始消息\n\n=== 可用工具列表 ===\n已有内容"

    injected = ToolsReminder.inject_tools_to_message(
        message,
        context=None,
        tool_source=[make_tool("plugin_tool", active=True)],
    )

    assert injected == message
    assert injected.count("=== 可用工具列表 ===") == 1


def test_inject_tools_to_message_returns_original_when_final_tool_source_empty():
    message = "原始消息"

    injected = ToolsReminder.inject_tools_to_message(
        message,
        context=None,
        tool_source=[],
    )

    assert injected == message

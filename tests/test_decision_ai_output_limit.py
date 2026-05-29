import importlib.util
import asyncio
import sys
import types
from pathlib import Path
from types import SimpleNamespace

import pytest


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
astrbot_api_all_module.AstrMessageEvent = object
astrbot_api_all_module.logger = DummyLogger()
astrbot_api_module.logger = astrbot_api_all_module.logger
sys.modules.setdefault("astrbot", astrbot_module)
sys.modules.setdefault("astrbot.api", astrbot_api_module)
sys.modules.setdefault("astrbot.api.all", astrbot_api_all_module)

decision_ai_path = (
    Path(__file__).resolve().parents[1] / "utils" / "decision_ai.py"
)
root = Path(__file__).resolve().parents[1]
package = types.ModuleType("astrbot_plugin_group_chat_plus")
package.__path__ = [str(root)]
sys.modules.setdefault("astrbot_plugin_group_chat_plus", package)
utils_package = types.ModuleType("astrbot_plugin_group_chat_plus.utils")
utils_package.__path__ = [str(root / "utils")]
sys.modules.setdefault("astrbot_plugin_group_chat_plus.utils", utils_package)

spec = importlib.util.spec_from_file_location(
    "astrbot_plugin_group_chat_plus.utils.decision_ai_under_test",
    decision_ai_path,
)
decision_ai_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(decision_ai_module)
DecisionAI = decision_ai_module.DecisionAI


class DummyProvider:
    def __init__(self, completion_text):
        self.completion_text = completion_text
        self.last_kwargs = None

    async def text_chat(self, **kwargs):
        self.last_kwargs = kwargs
        return SimpleNamespace(completion_text=self.completion_text)


class DummyPersonaManager:
    async def get_default_persona_v3(self, unified_msg_origin):
        return {"name": "default", "prompt": "persona"}


class DummyContext:
    def __init__(self, provider):
        self.provider = provider
        self.persona_manager = DummyPersonaManager()

    def get_using_provider(self):
        return self.provider

    def get_provider_by_id(self, provider_id):
        return self.provider


class DummyEvent:
    unified_msg_origin = "group:test"

    def get_sender_id(self):
        return "10001"

    def get_sender_name(self):
        return "Alice"


def test_should_reply_limits_decision_ai_output_kwargs():
    provider = DummyProvider("yes")

    result = asyncio.run(
        DecisionAI.should_reply(
            DummyContext(provider),
            DummyEvent(),
            "当前消息: 你好",
            provider_id="",
            extra_prompt="",
            max_tokens=4,
        )
    )

    assert result is True
    assert provider.last_kwargs["max_tokens"] == 4
    assert provider.last_kwargs["temperature"] == 0
    assert provider.last_kwargs["stop"] == ["\n", "。", "，"]
    assert "只能输出一个英文单词：yes 或 no" in provider.last_kwargs["prompt"]


def test_call_decision_ai_can_skip_persona_for_internal_classifier():
    provider = DummyProvider("正常")

    result = asyncio.run(
        DecisionAI.call_decision_ai(
            DummyContext(provider),
            DummyEvent(),
            "判断频率",
            use_persona=False,
            system_prompt_override="内部分类器",
            max_tokens=4,
            temperature=0,
            stop=["\n", "。"],
        )
    )

    assert result == "正常"
    assert provider.last_kwargs["system_prompt"] == "内部分类器"
    assert provider.last_kwargs["max_tokens"] == 4
    assert provider.last_kwargs["temperature"] == 0
    assert provider.last_kwargs["stop"] == ["\n", "。"]


def test_call_decision_ai_override_mode_skips_persona_by_default():
    provider = DummyProvider("正常")

    asyncio.run(
        DecisionAI.call_decision_ai(
            DummyContext(provider),
            DummyEvent(),
            "判断频率",
            prompt_mode="override",
        )
    )

    assert provider.last_kwargs["system_prompt"] == ""


@pytest.mark.parametrize(
    ("completion_text", "expected"),
    [
        ("yes", True),
        ("no", False),
        ("yes，因为我觉得应该参与", True),
        ("<think>先分析一下</think>\nno", False),
    ],
)
def test_should_reply_parses_short_and_noisy_decision_outputs(
    completion_text, expected
):
    provider = DummyProvider(completion_text)

    result = asyncio.run(
        DecisionAI.should_reply(
            DummyContext(provider),
            DummyEvent(),
            "当前消息: 你好",
            provider_id="",
            extra_prompt="",
            max_tokens=4,
        )
    )

    assert result is expected


def test_parse_decision_prefers_first_yes_no_token_in_long_output():
    assert DecisionAI._parse_decision("yes, because this is relevant") is True
    assert DecisionAI._parse_decision("no, because they are talking to others") is False

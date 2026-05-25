import asyncio
import sys
import types
from pathlib import Path
from types import SimpleNamespace


root = Path(__file__).resolve().parents[1]
package = types.ModuleType("astrbot_plugin_group_chat_plus")
package.__path__ = [str(root)]
if not hasattr(sys.modules.get("astrbot_plugin_group_chat_plus"), "__path__"):
    sys.modules["astrbot_plugin_group_chat_plus"] = package
utils_package = types.ModuleType("astrbot_plugin_group_chat_plus.utils")
utils_package.__path__ = [str(root / "utils")]
if not hasattr(sys.modules.get("astrbot_plugin_group_chat_plus.utils"), "__path__"):
    sys.modules["astrbot_plugin_group_chat_plus.utils"] = utils_package


class Plain:
    def __init__(self, text):
        self.text = text


class Image:
    def __init__(self, path):
        self.path = path

    async def convert_to_file_path(self):
        return self.path


class At:
    qq = "1"


class Face:
    id = "1"


class Reply:
    pass


logger = types.SimpleNamespace(
    info=lambda *args, **kwargs: None,
    warning=lambda *args, **kwargs: None,
    error=lambda *args, **kwargs: None,
    debug=lambda *args, **kwargs: None,
)
astrbot_module = sys.modules.setdefault("astrbot", types.ModuleType("astrbot"))
api_module = sys.modules.setdefault("astrbot.api", types.ModuleType("astrbot.api"))
api_all = sys.modules.setdefault("astrbot.api.all", types.ModuleType("astrbot.api.all"))
api_components = sys.modules.setdefault(
    "astrbot.api.message_components", types.ModuleType("astrbot.api.message_components")
)
api_module.logger = logger
api_all.logger = logger
api_all.Plain = Plain
api_all.Image = Image
api_all.BaseMessageComponent = object
api_all.AstrMessageEvent = object
api_all.Context = object
api_components.At = At
api_components.Face = Face
api_components.Reply = Reply

sys.modules.pop("astrbot_plugin_group_chat_plus.utils.global_time_control", None)
sys.modules.pop("astrbot_plugin_group_chat_plus.utils.image_importance_policy", None)
sys.modules.pop("astrbot_plugin_group_chat_plus.utils.image_gate_prompt", None)
sys.modules.pop("astrbot_plugin_group_chat_plus.utils.image_handler", None)

from astrbot_plugin_group_chat_plus.utils import image_gate_prompt as prompt_mod  # noqa: E402
from astrbot_plugin_group_chat_plus.utils.image_handler import ImageHandler  # noqa: E402


class FakeProvider:
    def __init__(self):
        self.calls = []

    async def text_chat(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(
            completion_text='{"description":"一张用于测试的图片","importance":0.8}'
        )


class FakeContext:
    def __init__(self, provider):
        self.provider = provider

    def get_provider_by_id(self, provider_id):
        assert provider_id == "vision"
        return self.provider


def run(coro):
    return asyncio.run(coro)


def test_structured_prompt_uses_system_prompt_and_keeps_user_prompt_task_only():
    async def scenario():
        provider = FakeProvider()
        image1 = Image("img-1.png")
        image2 = Image("img-2.png")

        text, statuses = await ImageHandler._convert_images_to_text(
            [Plain("看看这个"), image1, image2],
            FakeContext(provider),
            "vision",
            "请详细描述这张图片的内容",
            [image1, image2],
            image_to_text_system_prompt="补充：优先识别梗图含义。",
        )

        assert "[图片内容: 一张用于测试的图片]" in text
        assert len(statuses) == 2
        assert len(provider.calls) == 2

        assert "严格 JSON" in prompt_mod.build_structured_system_prompt("")

        first_call = provider.calls[0]
        assert first_call["system_prompt"]
        assert "JSON" in first_call["system_prompt"]
        assert "补充：优先识别梗图含义。" in first_call["system_prompt"]
        assert '{"description"' not in first_call["prompt"]
        assert "格式必须" not in first_call["prompt"]
        assert "看看这个" in first_call["prompt"]

        second_call = provider.calls[1]
        assert "[上文图片]" in second_call["prompt"]
        assert "当前消息共 2 张图片，本图是第 2 张。" in second_call["prompt"]

    run(scenario())


def test_burst_context_hint_compresses_previous_images():
    hint = ImageHandler._build_image_context_hint(
        [Plain(""), Image("img-1.png"), Image("img-2.png"), Image("img-3.png")],
        image_index=2,
        image_count=3,
        burst_factor=0.25,
    )

    assert "[上文连续图片×2]" in hint
    assert "当前消息共 3 张图片，本图是第 3 张。" in hint
    assert "[近期群内图片较多，前文图片已压缩]" in hint


def test_structured_parser_rejects_unexpected_fields():
    desc, importance, ok, reason = ImageHandler._parse_structured_image_response(
        '{"description":"图片","importance":0.5,"extra":"bad"}'
    )

    assert desc == ""
    assert importance == 0.0
    assert ok is False
    assert reason == "unexpected_fields"

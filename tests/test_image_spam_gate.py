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
api_components.Reply = Reply
api_components.At = type("At", (), {"qq": "1"})
api_components.Face = type("Face", (), {"id": "1"})


from astrbot_plugin_group_chat_plus.utils.image_handler import ImageHandler  # noqa: E402
from astrbot_plugin_group_chat_plus.utils.image_spam_gate import (  # noqa: E402
    ImageSpamGate,
)
HandlerImage = sys.modules["astrbot_plugin_group_chat_plus.utils.image_handler"].Image
HandlerPlain = sys.modules["astrbot_plugin_group_chat_plus.utils.image_handler"].Plain
HandlerReply = sys.modules["astrbot_plugin_group_chat_plus.utils.image_handler"].Reply


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
        return "u1"

    def get_message_outline(self):
        return "[outline]"


def run(coro):
    return asyncio.run(coro)


class CountingPolicy:
    enabled = True

    def __init__(self):
        self.register_calls = []

    def register_image_batch(self, *, chat_key, image_count, timestamp):
        self.register_calls.append((chat_key, image_count))
        return 1.0

    def batch_factor(self, image_count):
        return 1.0

    def evaluate(self, *, model_importance, burst_factor, batch_factor):
        return SimpleNamespace(
            to_dict=lambda: {
                "keep": True,
                "importance": model_importance,
                "effective_importance": model_importance,
                "time_factor": 1.0,
                "burst_factor": burst_factor,
                "batch_factor": batch_factor,
                "threshold": 0.0,
                "gate_reason": "test",
                "policy_version": "test",
            }
        )


class CountingSpamGate:
    def __init__(self):
        self.calls = 0

    def evaluate(self, **_kwargs):
        self.calls += 1
        return SimpleNamespace(skip=False, reason="")


def test_active_image_blacklist_skips_provider_and_marks_pending_retry():
    async def scenario():
        provider = FakeProvider()
        images = [HandlerImage("blocked.png")]
        event = DummyEvent([HandlerPlain("看看"), *images])

        should_continue, text, image_urls, retained, statuses = (
            await ImageHandler.process_message_images(
                event,
                FakeContext(provider),
                True,
                "all",
                "vision",
                "describe image",
                False,
                False,
                timeout=3,
                image_description_cache=None,
                max_images_per_message=20,
                image_importance_policy=None,
                image_spam_gate=None,
                image_to_text_system_prompt="",
                skip_active_image_understanding=True,
            )
        )

        assert should_continue is True
        assert provider.calls == []
        assert image_urls == []
        assert retained is False
        assert "看看" in text
        assert statuses == [
            {
                "index": 0,
                "image_ref": "blocked.png",
                "status": "pending_retry",
                "description": "",
                "failure_reason": "active_image_blacklist",
                "importance": 0.0,
                "effective_importance": 0.0,
                "keep": False,
                "gate_reason": "active_image_blacklist",
                "policy_version": "image_importance_gate_v1",
            }
        ]

    run(scenario())


def test_provider_image_path_registers_importance_and_spam_gate_once():
    async def scenario():
        provider = FakeProvider()
        policy = CountingPolicy()
        spam_gate = CountingSpamGate()
        images = [HandlerImage("img-once.png")]
        event = DummyEvent([HandlerPlain("看看"), *images])

        should_continue, text, _, retained, statuses = await ImageHandler.process_message_images(
            event,
            FakeContext(provider),
            True,
            "all",
            "vision",
            "请描述图片",
            False,
            False,
            timeout=3,
            image_description_cache=None,
            max_images_per_message=20,
            image_importance_policy=policy,
            image_spam_gate=spam_gate,
            image_to_text_system_prompt="",
        )

        assert should_continue is True
        assert "[图片内容: 一张用于测试的图片]" in text
        assert retained is True
        assert len(statuses) == 1
        assert len(provider.calls) == 1
        assert policy.register_calls == [("qq:100", 1)]
        assert spam_gate.calls == 1

    run(scenario())


def test_active_image_blacklist_skips_multimodal_image_urls():
    async def scenario():
        provider = FakeProvider()
        images = [HandlerImage("blocked-url.png")]
        event = DummyEvent(images)

        should_continue, text, image_urls, retained, statuses = (
            await ImageHandler.process_message_images(
                event,
                FakeContext(provider),
                True,
                "all",
                "",
                "describe image",
                False,
                False,
                timeout=3,
                image_description_cache=None,
                max_images_per_message=20,
                image_importance_policy=None,
                image_spam_gate=None,
                image_to_text_system_prompt="",
                skip_active_image_understanding=True,
            )
        )

        assert should_continue is True
        assert provider.calls == []
        assert image_urls == []
        assert retained is False
        assert text
        assert statuses[0]["status"] == "pending_retry"
        assert statuses[0]["failure_reason"] == "active_image_blacklist"

    run(scenario())


def test_brush_batch_skips_vision_calls_and_returns_placeholders():
    async def scenario():
        provider = FakeProvider()
        images = [HandlerImage(f"img-{idx}.png") for idx in range(11)]
        event = DummyEvent(images)

        should_continue, text, _, retained, statuses = await ImageHandler.process_message_images(
            event,
            FakeContext(provider),
            True,
            "all",
            "vision",
            "请描述图片",
            False,
            False,
            timeout=3,
            image_description_cache=None,
            max_images_per_message=20,
            image_importance_policy=None,
            image_spam_gate=ImageSpamGate(
                enabled=True,
                batch_soft_limit=2,
                batch_hard_limit=6,
                cooldown_seconds=120,
                log_decisions=False,
            ),
            image_to_text_system_prompt="",
        )

        assert should_continue is True
        assert provider.calls == []
        assert text.count("[") == 11
        assert retained is False
        assert statuses
        assert all(item["status"] == "skipped_spam_batch" for item in statuses)

    run(scenario())


def test_reply_bypass_still_calls_vision_on_large_batch():
    async def scenario():
        provider = FakeProvider()
        images = [HandlerImage(f"img-{idx}.png") for idx in range(8)]
        event = DummyEvent([HandlerReply(), *images])

        should_continue, text, _, retained, statuses = await ImageHandler.process_message_images(
            event,
            FakeContext(provider),
            True,
            "all",
            "vision",
            "请描述图片",
            False,
            False,
            timeout=3,
            image_description_cache=None,
            max_images_per_message=20,
            image_importance_policy=None,
            image_spam_gate=ImageSpamGate(
                enabled=True,
                batch_soft_limit=2,
                batch_hard_limit=6,
                cooldown_seconds=120,
                log_decisions=False,
            ),
            image_to_text_system_prompt="",
        )

        assert should_continue is True
        assert len(provider.calls) == 8
        assert retained is True
        assert statuses
        assert all(item["status"] == "success" for item in statuses)
        assert text.count("[") >= 8

    run(scenario())

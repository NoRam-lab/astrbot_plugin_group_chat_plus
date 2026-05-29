import asyncio
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

    def debug(self, *args, **kwargs):
        pass


class DummySp:
    value = {}

    @classmethod
    async def get_async(cls, *args, **kwargs):
        return cls.value


def load_memory_injector():
    root = Path(__file__).resolve().parents[1]

    api_module = types.ModuleType("astrbot.api")
    api_module.sp = DummySp
    api_module.logger = DummyLogger()

    api_all_module = types.ModuleType("astrbot.api.all")
    api_all_module.Context = object
    api_all_module.AstrMessageEvent = object
    api_all_module.logger = api_module.logger

    sys.modules["astrbot.api"] = api_module
    sys.modules["astrbot.api.all"] = api_all_module

    memory_injector_path = root / "utils" / "memory_injector.py"
    spec = importlib.util.spec_from_file_location(
        "astrbot_plugin_group_chat_plus.utils.memory_injector_under_test",
        memory_injector_path,
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.MemoryInjector


MemoryInjector = load_memory_injector()


class DummyConversationManager:
    def __init__(self, persona_id=None, curr_cid="cid-1"):
        self.persona_id = persona_id
        self.curr_cid = curr_cid

    async def get_curr_conversation_id(self, umo):
        return self.curr_cid

    async def get_conversation(self, umo, curr_cid):
        return SimpleNamespace(persona_id=self.persona_id)


class DummyPersonaManager:
    def __init__(self, default_persona="default-persona"):
        self.default_persona = default_persona

    async def get_default_persona_v3(self, umo=None):
        return {"name": self.default_persona}


class DummyContext:
    def __init__(self, conversation_persona=None, default_persona="default-persona"):
        self.conversation_manager = DummyConversationManager(conversation_persona)
        self.persona_manager = DummyPersonaManager(default_persona)


class DummyEvent:
    unified_msg_origin = "bot1:GroupMessage:927287190"


def test_session_service_persona_takes_priority():
    DummySp.value = {"persona_id": "session-persona"}

    result = asyncio.run(
        MemoryInjector._get_current_persona_id(
            DummyContext(conversation_persona="conversation-persona"),
            DummyEvent(),
        )
    )

    assert result == "session-persona"


def test_conversation_persona_used_when_no_session_override():
    DummySp.value = {}

    result = asyncio.run(
        MemoryInjector._get_current_persona_id(
            DummyContext(conversation_persona="conversation-persona"),
            DummyEvent(),
        )
    )

    assert result == "conversation-persona"


def test_explicit_none_persona_does_not_fall_back_to_default():
    DummySp.value = {}

    result = asyncio.run(
        MemoryInjector._get_current_persona_id(
            DummyContext(conversation_persona="[%None]"),
            DummyEvent(),
        )
    )

    assert result is None


def test_default_persona_used_as_final_fallback():
    DummySp.value = {}

    result = asyncio.run(
        MemoryInjector._get_current_persona_id(
            DummyContext(conversation_persona=None, default_persona="default-persona"),
            DummyEvent(),
        )
    )

    assert result == "default-persona"

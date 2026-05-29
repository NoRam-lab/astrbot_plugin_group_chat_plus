import asyncio
import logging
from types import SimpleNamespace

from test_decision_context_limits import ChatPlus

import sys


main_module = sys.modules["astrbot_plugin_group_chat_plus.main_under_test"]


class StringifyingHandler(logging.Handler):
    def emit(self, record):
        record.args = tuple(str(arg) for arg in (record.args or ()))
        record.getMessage()


class FakeStore:
    def __init__(self):
        self.rows = []

    async def upsert_image_status(self, row):
        self.rows.append(row)


class FakeEvent:
    def __init__(self):
        self.message_obj = SimpleNamespace(message_id="msg-1")

    def get_platform_id(self):
        return "qq"

    def get_platform_name(self):
        return "aiocqhttp"

    def is_private_chat(self):
        return False

    def get_group_id(self):
        return "group-1"

    def get_sender_id(self):
        return "user-1"


def test_record_image_status_logging_survives_stringified_args(monkeypatch):
    async def scenario():
        plugin = ChatPlus.__new__(ChatPlus)
        plugin.debug_mode = False
        plugin.enable_image_importance_gate_log = True

        store = FakeStore()
        monkeypatch.setattr(main_module.ContextManager, "sqlite_store", store, raising=False)

        test_logger = logging.getLogger("gcp-image-status-test")
        test_logger.handlers = []
        test_logger.propagate = False
        test_logger.setLevel(logging.INFO)
        test_logger.addHandler(StringifyingHandler())
        monkeypatch.setattr(main_module, "logger", test_logger, raising=False)

        await plugin._record_image_statuses(
            FakeEvent(),
            [
                {
                    "status": "success",
                    "image_ref": "img-ref",
                    "index": 0,
                    "keep": False,
                    "importance": 0.18,
                    "effective_importance": 0.066,
                    "time_factor": 1.0,
                    "burst_factor": 0.3666666667,
                    "batch_factor": 1.0,
                    "threshold": 0.4,
                    "gate_reason": "burst_factor=0.37",
                }
            ],
        )

        assert len(store.rows) == 1

    asyncio.run(scenario())

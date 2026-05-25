import sys
import types
from datetime import datetime
from pathlib import Path


root = Path(__file__).resolve().parents[1]
package = types.ModuleType("astrbot_plugin_group_chat_plus")
package.__path__ = [str(root)]
if not hasattr(sys.modules.get("astrbot_plugin_group_chat_plus"), "__path__"):
    sys.modules["astrbot_plugin_group_chat_plus"] = package
utils_package = types.ModuleType("astrbot_plugin_group_chat_plus.utils")
utils_package.__path__ = [str(root / "utils")]
if not hasattr(sys.modules.get("astrbot_plugin_group_chat_plus.utils"), "__path__"):
    sys.modules["astrbot_plugin_group_chat_plus.utils"] = utils_package
sys.modules.pop("astrbot_plugin_group_chat_plus.utils.global_time_control", None)
sys.modules.pop("astrbot_plugin_group_chat_plus.utils.image_importance_policy", None)


logger = types.SimpleNamespace(
    info=lambda *args, **kwargs: None,
    warning=lambda *args, **kwargs: None,
    error=lambda *args, **kwargs: None,
    debug=lambda *args, **kwargs: None,
)
astrbot_module = sys.modules.setdefault("astrbot", types.ModuleType("astrbot"))
api_module = sys.modules.setdefault("astrbot.api", types.ModuleType("astrbot.api"))
api_all = sys.modules.setdefault("astrbot.api.all", types.ModuleType("astrbot.api.all"))
api_module.logger = getattr(api_module, "logger", logger)
api_all.logger = getattr(api_all, "logger", logger)


from astrbot_plugin_group_chat_plus.utils.global_time_control import (  # noqa: E402
    GlobalTimeControlManager,
)
from astrbot_plugin_group_chat_plus.utils.image_importance_policy import (  # noqa: E402
    ImageImportancePolicy,
)


def test_burst_factor_decays_between_soft_and_hard_limits():
    policy = ImageImportancePolicy(
        enabled=True,
        keep_threshold=0.35,
        burst_window_seconds=10,
        burst_soft_limit=2,
        burst_hard_limit=4,
        burst_min_factor=0.2,
    )

    assert policy.register_image_batch(chat_key="qq:100", image_count=1, timestamp=100) == 1.0
    assert policy.register_image_batch(chat_key="qq:100", image_count=1, timestamp=101) == 1.0
    assert policy.register_image_batch(chat_key="qq:100", image_count=1, timestamp=102) == 0.6
    assert policy.register_image_batch(chat_key="qq:100", image_count=1, timestamp=103) == 0.2


def test_batch_factor_decays_between_soft_and_hard_limits():
    policy = ImageImportancePolicy(
        enabled=True,
        keep_threshold=0.35,
        batch_soft_limit=2,
        batch_hard_limit=4,
        batch_min_factor=0.2,
    )

    assert policy.batch_factor(1) == 1.0
    assert policy.batch_factor(2) == 1.0
    assert policy.batch_factor(3) == 0.6
    assert policy.batch_factor(4) == 0.2


def test_time_rule_image_factor_affects_effective_importance():
    GlobalTimeControlManager.initialize(
        {
            "enable_global_time_control": True,
            "global_time_control_rules": [
                {
                    "name": "low",
                    "start": "00:00",
                    "end": "23:59",
                    "normal_probability_factor": 1.0,
                    "forced_trigger_probability": 1.0,
                    "image_importance_factor": 0.2,
                }
            ],
        }
    )
    policy = ImageImportancePolicy(enabled=True, keep_threshold=0.35)
    decision = policy.evaluate(
        model_importance=0.8,
        burst_factor=1.0,
        now=datetime(2026, 1, 1, 12, 0),
    )

    assert decision.keep is False
    assert decision.time_factor == 0.2
    assert round(decision.effective_importance, 3) == 0.16

    GlobalTimeControlManager.initialize({"enable_global_time_control": False})

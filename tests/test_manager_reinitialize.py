import importlib.util
import sys
import types
from pathlib import Path


def load_manager_classes():
    if "astrbot.api.all" not in sys.modules:
        astrbot_module = types.ModuleType("astrbot")
        api_module = types.ModuleType("astrbot.api")
        api_all = types.ModuleType("astrbot.api.all")
        logger = types.SimpleNamespace(
            info=lambda *args, **kwargs: None,
            warning=lambda *args, **kwargs: None,
            error=lambda *args, **kwargs: None,
            debug=lambda *args, **kwargs: None,
        )
        api_module.logger = logger
        api_all.logger = logger
        sys.modules.setdefault("astrbot", astrbot_module)
        sys.modules["astrbot.api"] = api_module
        sys.modules["astrbot.api.all"] = api_all

    utils_dir = Path(__file__).resolve().parents[1] / "utils"
    package_name = "gcp_manager_reinitialize_under_test"
    package = types.ModuleType(package_name)
    package.__path__ = [str(utils_dir)]
    sys.modules[package_name] = package

    cooldown_spec = importlib.util.spec_from_file_location(
        f"{package_name}.cooldown_manager",
        utils_dir / "cooldown_manager.py",
    )
    cooldown_module = importlib.util.module_from_spec(cooldown_spec)
    sys.modules[cooldown_spec.name] = cooldown_module
    cooldown_spec.loader.exec_module(cooldown_module)

    attention_spec = importlib.util.spec_from_file_location(
        f"{package_name}.attention_manager",
        utils_dir / "attention_manager.py",
    )
    attention_module = importlib.util.module_from_spec(attention_spec)
    sys.modules[attention_spec.name] = attention_module
    attention_spec.loader.exec_module(attention_module)

    return cooldown_module.CooldownManager, attention_module.AttentionManager


CooldownManager, AttentionManager = load_manager_classes()


def cooldown_config(duration=600, threshold=0.3, decrease=0.2):
    return {
        "cooldown_max_duration": duration,
        "cooldown_trigger_threshold": threshold,
        "cooldown_attention_decrease": decrease,
    }


def attention_config(*, spillover_ratio=0.35, fatigue_reset=300):
    return {
        "enable_attention_emotion_detection": True,
        "attention_emotion_keywords": {"positive": ["ok"], "negative": ["bad"]},
        "attention_enable_negation": True,
        "attention_negation_words": ["not"],
        "attention_negation_check_range": 5,
        "attention_positive_emotion_boost": 0.1,
        "attention_negative_emotion_decrease": 0.15,
        "enable_attention_spillover": True,
        "attention_spillover_ratio": spillover_ratio,
        "attention_spillover_decay_halflife": 90,
        "attention_spillover_min_trigger": 0.4,
        "enable_conversation_fatigue": True,
        "fatigue_reset_threshold": fatigue_reset,
        "fatigue_threshold_light": 3,
        "fatigue_threshold_medium": 5,
        "fatigue_threshold_heavy": 8,
        "fatigue_probability_decrease_light": 0.1,
        "fatigue_probability_decrease_medium": 0.2,
        "fatigue_probability_decrease_heavy": 0.35,
    }


def reset_cooldown_manager():
    CooldownManager._cooldown_map = {}
    CooldownManager._storage_path = None
    CooldownManager._initialized = False
    CooldownManager.MAX_COOLDOWN_DURATION = 600
    CooldownManager.COOLDOWN_TRIGGER_THRESHOLD = 0.3
    CooldownManager.COOLDOWN_ATTENTION_DECREASE = 0.2


def reset_attention_manager():
    AttentionManager._attention_map = {}
    AttentionManager._conversation_activity_map = {}
    AttentionManager._fatigue_attention_block = {}
    AttentionManager._storage_path = None
    AttentionManager._initialized = False
    AttentionManager.SPILLOVER_RATIO = 0.35
    AttentionManager.CONSECUTIVE_REPLY_RESET_THRESHOLD = 300


def test_cooldown_initialize_reapplies_config_on_same_path(tmp_path):
    reset_cooldown_manager()
    data_dir = tmp_path / "data"

    CooldownManager.initialize(str(data_dir), cooldown_config(duration=111))
    CooldownManager._cooldown_map["chat"] = {"user": {"cooldown_start": 1}}

    CooldownManager.initialize(str(data_dir), cooldown_config(duration=222))

    assert CooldownManager.MAX_COOLDOWN_DURATION == 222
    assert "chat" in CooldownManager._cooldown_map


def test_cooldown_initialize_clears_stale_state_when_path_changes(tmp_path):
    reset_cooldown_manager()
    CooldownManager.initialize(str(tmp_path / "old"), cooldown_config(duration=111))
    CooldownManager._cooldown_map["stale"] = {"user": {"cooldown_start": 1}}

    CooldownManager.initialize(str(tmp_path / "new"), cooldown_config(duration=222))

    assert CooldownManager.MAX_COOLDOWN_DURATION == 222
    assert CooldownManager._cooldown_map == {}


def test_attention_initialize_reapplies_config_on_same_path(tmp_path):
    reset_attention_manager()
    data_dir = tmp_path / "data"

    AttentionManager.initialize(
        str(data_dir),
        attention_config(spillover_ratio=0.2, fatigue_reset=100),
    )
    AttentionManager._attention_map["chat"] = {"user": {"attention_score": 0.5}}

    AttentionManager.initialize(
        str(data_dir),
        attention_config(spillover_ratio=0.6, fatigue_reset=200),
    )

    assert AttentionManager.SPILLOVER_RATIO == 0.6
    assert AttentionManager.CONSECUTIVE_REPLY_RESET_THRESHOLD == 200
    assert "chat" in AttentionManager._attention_map


def test_attention_initialize_clears_stale_state_when_path_changes(tmp_path):
    reset_attention_manager()
    AttentionManager.initialize(str(tmp_path / "old"), attention_config())
    AttentionManager._attention_map["stale"] = {"user": {"attention_score": 0.5}}
    AttentionManager._conversation_activity_map["stale"] = {"activity_score": 0.8}
    AttentionManager._fatigue_attention_block["stale"] = {"user": {"blocked_at": 1}}

    AttentionManager.initialize(
        str(tmp_path / "new"),
        attention_config(spillover_ratio=0.7, fatigue_reset=400),
    )

    assert AttentionManager.SPILLOVER_RATIO == 0.7
    assert AttentionManager.CONSECUTIVE_REPLY_RESET_THRESHOLD == 400
    assert AttentionManager._attention_map == {}
    assert AttentionManager._conversation_activity_map == {}
    assert AttentionManager._fatigue_attention_block == {}

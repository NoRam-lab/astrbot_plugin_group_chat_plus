import importlib.util
from pathlib import Path


def load_module(name):
    path = Path(__file__).resolve().parents[1] / "utils" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"{name}_under_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


RuntimeMessageSnapshotStore = load_module(
    "runtime_message_snapshot_store"
).RuntimeMessageSnapshotStore
WaitWindowBuffer = load_module("wait_window_buffer").WaitWindowBuffer


def test_runtime_snapshot_store_copies_and_pops():
    store = RuntimeMessageSnapshotStore()
    original = {"content": "hello", "image_refs": ["a"], "chat_id": "100"}

    store.put("m1", original)
    original["image_refs"].append("mutated")

    first = store.get("m1")
    assert first == {"content": "hello", "image_refs": ["a"], "chat_id": "100"}
    first["content"] = "changed"

    popped = store.pop("m1")
    assert popped["content"] == "hello"
    assert store.pop("m1") is None


def test_runtime_snapshot_store_clear_chat():
    store = RuntimeMessageSnapshotStore()
    store.put("m1", {"chat_id": "100", "content": "a"})
    store.put("m2", {"chat_id": "200", "content": "b"})

    assert store.clear_chat("100") == 1
    assert store.get("m1") is None
    assert store.get("m2")["content"] == "b"


def test_wait_window_buffer_orders_trims_and_copies():
    buffer = WaitWindowBuffer(max_messages=2)
    buffer.add("100", {"message_id": "late", "timestamp": 3, "content": "late"})
    buffer.add("100", {"message_id": "early", "timestamp": 1, "content": "early"})
    buffer.add("100", {"message_id": "middle", "timestamp": 2, "content": "middle"})

    items = buffer.get("100")
    assert [item["message_id"] for item in items] == ["middle", "late"]
    assert all(item["window_buffered"] for item in items)

    items[0]["content"] = "changed"
    assert buffer.get("100")[0]["content"] == "middle"


def test_wait_window_buffer_clear_by_ids_and_all():
    buffer = WaitWindowBuffer(max_messages=5)
    buffer.add("100", {"message_id": "a", "timestamp": 1})
    buffer.add("100", {"message_id": "b", "timestamp": 2})
    buffer.add("200", {"message_id": "c", "timestamp": 3})

    assert buffer.clear("100", saved_msg_ids={"a"}) == 1
    assert [item["message_id"] for item in buffer.get("100")] == ["b"]
    assert buffer.clear_all() == 2
    assert buffer.chat_ids() == []


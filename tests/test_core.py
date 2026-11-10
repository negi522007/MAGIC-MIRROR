from config import DEFAULTS, _deep_merge, load_config, resolve_path
from core.event_bus import EventBus
from core.state_manager import StateManager


def test_bus_isolates_failing_callback():
    bus, received = EventBus(), []
    bus.subscribe("e", lambda d: 1 / 0)
    bus.subscribe("e", received.append)
    bus.emit("e", 42)
    assert received == [42]


def test_state_manager_emits_state_name():
    bus, states = EventBus(), []
    bus.subscribe("state_changed", states.append)
    sm = StateManager(bus)
    assert sm.set_state("listening")
    assert not sm.set_state("speaking")          # listening -> speaking interdit
    assert sm.set_state("speaking", force=True)
    assert states == ["listening", "speaking"]


def test_try_begin_only_once():
    sm = StateManager()
    assert sm.try_begin("idle", "listening")
    assert not sm.try_begin("idle", "listening")  # second mot clé ignoré


def test_config_defaults_and_merge(tmp_path):
    p = tmp_path / "c.yaml"
    p.write_text("camera:\n  index: 2\n")
    cfg = load_config(str(p))
    assert cfg["camera"]["index"] == 2
    assert cfg["camera"]["width"] == DEFAULTS["camera"]["width"]
    assert _deep_merge({"a": {"b": 1}}, {"a": {"c": 2}}) == {"a": {"b": 1, "c": 2}}


def test_project_config_points_to_existing_vosk_model():
    cfg = load_config()
    import os
    assert os.path.isdir(resolve_path(cfg["models"]["vosk"])), \
        "config.yaml doit pointer vers le dossier Vosk réellement présent dans models/"

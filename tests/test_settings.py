import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from settings import DEFAULTS, load_settings, save_setting  # noqa: E402


def test_missing_file_gives_defaults_and_creates_it(tmp_path):
    path = tmp_path / "settings.json"
    s = load_settings(path)
    assert s["camera"] == 0 and s["pause_hotkey"] == "ctrl+alt+p" and s["dwell_s"] == 0.5
    assert json.loads(path.read_text()) == DEFAULTS


def test_old_file_without_new_keys_gets_defaults_for_them(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({"dwell_s": 0.4}))
    s = load_settings(path)
    assert s["dwell_s"] == 0.4 and s["camera"] == 0 and s["pause_hotkey"] == "ctrl+alt+p"


def test_save_setting_keeps_other_values(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({"dwell_s": 0.4, "suspend_when_foreground": ["Game.exe"]}))
    save_setting("camera", 2, path)
    data = json.loads(path.read_text())
    assert data == {"dwell_s": 0.4, "suspend_when_foreground": ["Game.exe"], "camera": 2}
    assert load_settings(path)["suspend_when_foreground"] == ["game.exe"]


def test_corrupt_file_falls_back_to_defaults(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text("{not json")
    assert load_settings(path)["camera"] == 0

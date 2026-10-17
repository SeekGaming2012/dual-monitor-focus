"""User settings: a small JSON file next to the calibration. Created with defaults on first run."""
import json

from config import CONFIG_DIR

SETTINGS_PATH = CONFIG_DIR / "settings.json"

DEFAULTS = {
    # Which webcam to use (index shown in the tray's Camera menu).
    "camera": 0,
    "dwell_s": 0.5,
    # Global keyboard shortcut that pauses/resumes tracking. At least one of ctrl/alt/shift/win
    # is required. Set to "" to disable.
    "pause_hotkey": "ctrl+alt+p",
    # Process names (e.g. "game.exe") that are never chosen as the window to focus.
    "ignore_target_processes": [],
    # While one of these is the foreground app, no switching happens at all.
    "suspend_when_foreground": [],
}


def load_settings(path=SETTINGS_PATH):
    settings = dict(DEFAULTS)
    try:
        settings.update(json.loads(path.read_text()))
    except (OSError, ValueError):
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(DEFAULTS, indent=2))
        except OSError:
            pass
    settings["ignore_target_processes"] = [p.lower() for p in settings["ignore_target_processes"]]
    settings["suspend_when_foreground"] = [p.lower() for p in settings["suspend_when_foreground"]]
    return settings


def save_setting(key, value, path=SETTINGS_PATH):
    """Change one setting on disk, keeping everything else in the file as the user wrote it."""
    try:
        data = json.loads(path.read_text())
    except (OSError, ValueError):
        data = dict(DEFAULTS)
    data[key] = value
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2))

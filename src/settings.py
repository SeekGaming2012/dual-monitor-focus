"""User settings: a small JSON file next to the calibration. Created with defaults on first run."""
import json

from config import CONFIG_DIR

SETTINGS_PATH = CONFIG_DIR / "settings.json"

DEFAULTS = {
    "dwell_s": 0.5,
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

"""Calibration storage: a small JSON file in %APPDATA%. Contains angles only, never images."""
import json
import os
from pathlib import Path

CONFIG_DIR = Path(os.environ.get("APPDATA", Path.home())) / "dual-monitor-focus"
CONFIG_PATH = CONFIG_DIR / "calibration.json"


def save_calibration(data, path=CONFIG_PATH):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2))


def load_calibration(path=CONFIG_PATH):
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return None

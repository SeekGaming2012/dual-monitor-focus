"""Dual Monitor Focus: tray app that moves keyboard focus to the monitor you look at.

Run with `python main.py` (console) or `pythonw main.py` (no console window).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
from tray import main  # noqa: E402

if __name__ == "__main__":
    main()

"""Step 8: alternate keyboard focus between the topmost window on each monitor every 2 seconds.

Runs for 20 seconds. Type into each window as focus lands on it to confirm it receives
keystrokes. No camera is used.
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from focus import focus_window  # noqa: E402
from monitors import enable_dpi_awareness, list_monitors  # noqa: E402
from windows import topmost_window_on  # noqa: E402

DURATION_S = 20
INTERVAL_S = 2

sys.stdout.reconfigure(errors="replace")
enable_dpi_awareness()
monitors = list_monitors()
names = ["LEFT", "RIGHT"]
end = time.time() + DURATION_S
turn = 0
while time.time() < end:
    name, mon = names[turn % 2], monitors[turn % 2]
    w = topmost_window_on(mon)
    if w is None:
        print(f"{name}: no window to focus")
    else:
        how = focus_window(w.hwnd)
        print(f"{name}: {w.process}: {w.title[:50]} -> {f'focused ({how})' if how else 'FAILED'}")
    turn += 1
    time.sleep(INTERVAL_S)

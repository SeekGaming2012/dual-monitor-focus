"""Step 7: print the topmost window on each monitor, once a second for 15 seconds.

Click around, minimize windows, or drag one across monitors and watch the output change.
No camera is used.
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from monitors import enable_dpi_awareness, list_monitors  # noqa: E402
from windows import topmost_window_on  # noqa: E402

DURATION_S = 15

sys.stdout.reconfigure(errors="replace")  # window titles often contain characters the console can't show

enable_dpi_awareness()
monitors = list_monitors()
names = ["LEFT", "RIGHT"] if len(monitors) == 2 else [f"MON{i}" for i in range(len(monitors))]
end = time.time() + DURATION_S
last = None
while time.time() < end:
    now = []
    for name, mon in zip(names, monitors):
        w = topmost_window_on(mon)
        now.append((name, f"{w.process}: {w.title[:60]}" if w else "(no window)"))
    if now != last:
        print(time.strftime("%H:%M:%S"), " | ".join(f"{n}: {d}" for n, d in now))
        last = now
    time.sleep(1)

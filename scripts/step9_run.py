"""Step 9: hands-free focus switching, running in this console.

Look at a monitor for ~500 ms and keyboard focus moves to its topmost window.
Runs for --seconds (default 60), or until Ctrl+C. Needs a saved calibration (step 5).
Nothing is saved; frames are processed in memory only.
"""
import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from config import CONFIG_PATH, load_calibration  # noqa: E402
from monitors import enable_dpi_awareness, list_monitors  # noqa: E402
from worker import FocusWorker  # noqa: E402

parser = argparse.ArgumentParser()
parser.add_argument("--camera", type=int, default=0)
parser.add_argument("--dwell", type=float, default=0.5, help="seconds (default 0.5)")
parser.add_argument("--seconds", type=float, default=60)
args = parser.parse_args()

sys.stdout.reconfigure(errors="replace")
cal = load_calibration()
if cal is None:
    raise SystemExit(f"No calibration found at {CONFIG_PATH}. Run step5_calibrate.py first.")

enable_dpi_awareness()
layout = [[m.left, m.top, m.right, m.bottom] for m in list_monitors()]
if layout != cal.get("monitors"):
    print("Warning: the monitor layout changed since calibration; consider step5_calibrate.py --recalibrate")


def log(message):
    print(time.strftime("%H:%M:%S"), message, flush=True)


worker = FocusWorker(cal, camera_index=args.camera, settings={"dwell_s": args.dwell}, on_event=log)
worker.start()
log(f"running for {args.seconds:.0f}s (Ctrl+C to stop)")
try:
    time.sleep(args.seconds)
except KeyboardInterrupt:
    pass
worker.stop()
log("stopped")

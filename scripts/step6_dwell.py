"""Step 6: live test of the dwell filter using your saved calibration.

Shows the raw label, the pending candidate with a progress bar, and the committed side
(the one that would receive focus). Keys: [ and ] shorten/lengthen the dwell time.
Esc or q quits. Nothing is saved.
"""
import argparse
import sys
import time
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from camera import open_camera  # noqa: E402
from classify import Ema, SideClassifier  # noqa: E402
from config import CONFIG_PATH, load_calibration  # noqa: E402
from dwell import DwellFilter  # noqa: E402
from headpose import HeadPose  # noqa: E402

parser = argparse.ArgumentParser()
parser.add_argument("--camera", type=int, default=0)
parser.add_argument("--dwell", type=float, default=0.5, help="seconds (default 0.5)")
args = parser.parse_args()

cal = load_calibration()
if cal is None:
    raise SystemExit(f"No calibration found at {CONFIG_PATH}. Run step5_calibrate.py first.")

cap = open_camera(args.camera)
pose = HeadPose()
side = SideClassifier(cal["left"]["yaw"], cal["right"]["yaw"])
ema = Ema(alpha=0.3)
dwell = DwellFilter(dwell_s=args.dwell)
t0 = time.perf_counter()
COLORS = {"LEFT": (255, 160, 0), "RIGHT": (0, 160, 255), "UNKNOWN": (180, 180, 180), None: (180, 180, 180)}

while True:
    ok, frame = cap.read()
    if not ok:
        break
    now = time.perf_counter() - t0
    angles = pose.estimate(frame, now * 1000)
    if angles is None:
        ema.reset()
        yaw = None
    else:
        yaw = ema.update(angles[0])
    label = side.classify(yaw)
    switched = dwell.update(label, now)
    if switched:
        print(f"{now:7.2f}s  SWITCH -> {switched}")

    frame = cv2.flip(frame, 1)
    cv2.putText(frame, f"focus: {dwell.committed}", (10, 45), cv2.FONT_HERSHEY_SIMPLEX, 1.3,
                COLORS[dwell.committed], 3)
    cv2.putText(frame, f"looking: {label}   dwell {dwell.dwell_s * 1000:.0f} ms", (10, 80),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, COLORS[label], 2)
    cv2.rectangle(frame, (10, 95), (210, 110), (80, 80, 80), 2)
    cv2.rectangle(frame, (10, 95), (10 + int(200 * dwell.progress), 110), COLORS[dwell.candidate], -1)
    cv2.imshow("dwell test", frame)

    key = cv2.waitKey(1) & 0xFF
    if key in (27, ord("q")):
        break
    if key == ord("["):
        dwell.dwell_s = max(0.1, dwell.dwell_s - 0.05)
    elif key == ord("]"):
        dwell.dwell_s = min(1.5, dwell.dwell_s + 0.05)

pose.close()
cap.release()
cv2.destroyAllWindows()

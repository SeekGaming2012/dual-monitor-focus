"""Step 5: calibrate (left monitor, then right), save to JSON, then test live.

Runs calibration if none is saved, or with --recalibrate. Esc during calibration aborts.
In the live test, Esc or q quits. Nothing but angles is saved.
"""
import argparse
import sys
import time
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from calibration import CalibrationAborted, CalibrationFailed, run_calibration  # noqa: E402
from camera import open_camera  # noqa: E402
from classify import Ema, SideClassifier  # noqa: E402
from config import CONFIG_PATH, load_calibration, save_calibration  # noqa: E402
from headpose import HeadPose  # noqa: E402
from monitors import enable_dpi_awareness, list_monitors  # noqa: E402

parser = argparse.ArgumentParser()
parser.add_argument("--camera", type=int, default=0)
parser.add_argument("--recalibrate", action="store_true")
args = parser.parse_args()

enable_dpi_awareness()
monitors = list_monitors()
print(f"{len(monitors)} monitors:", [(m.left, m.top, m.width, m.height) for m in monitors])

cap = open_camera(args.camera)
pose = HeadPose()
cal = None if args.recalibrate else load_calibration()
try:
    if cal is None:
        print("Calibrating: look at each monitor when prompted (Esc aborts)...")
        cal = run_calibration(cap, pose, monitors, args.camera)
        save_calibration(cal)
        print(f"Saved to {CONFIG_PATH}")
    else:
        print(f"Using saved calibration from {CONFIG_PATH} (created {cal['created']})")
except (CalibrationAborted, CalibrationFailed) as e:
    print("Calibration did not complete:", e or "aborted")
    pose.close()
    cap.release()
    cv2.destroyAllWindows()
    raise SystemExit(1)

print(f"left yaw {cal['left']['yaw']:+.1f} (std {cal['left']['yaw_std']:.1f}), "
      f"right yaw {cal['right']['yaw']:+.1f} (std {cal['right']['yaw_std']:.1f}), "
      f"separation {cal['separation']:.1f} deg")

side = SideClassifier(cal["left"]["yaw"], cal["right"]["yaw"])
ema = Ema(alpha=0.3)
t0 = time.perf_counter()
COLORS = {"LEFT": (255, 160, 0), "RIGHT": (0, 160, 255), "UNKNOWN": (180, 180, 180)}
cv2.namedWindow("live test")
cv2.moveWindow("live test", 100, 100)
while True:
    ok, frame = cap.read()
    if not ok:
        break
    angles = pose.estimate(frame, (time.perf_counter() - t0) * 1000)
    if angles is None:
        ema.reset()
        yaw = None
    else:
        yaw = ema.update(angles[0])
    label = side.classify(yaw)
    frame = cv2.flip(frame, 1)
    cv2.putText(frame, label, (10, 45), cv2.FONT_HERSHEY_SIMPLEX, 1.5, COLORS[label], 3)
    cv2.putText(frame, "no face" if yaw is None else f"yaw {yaw:+6.1f}", (10, 85),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
    cv2.imshow("live test", frame)
    if cv2.waitKey(1) & 0xFF in (27, ord("q")):
        break

pose.close()
cap.release()
cv2.destroyAllWindows()

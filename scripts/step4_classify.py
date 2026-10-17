"""Step 4: smoothed yaw and a live LEFT/RIGHT/UNKNOWN label.

Look at your left monitor and press L, look at your right monitor and press R.
Press C to clear, Esc or q to quit. Nothing is saved.
"""
import sys
import time
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from camera import camera_arg, open_camera  # noqa: E402
from classify import Ema, SideClassifier  # noqa: E402
from headpose import HeadPose  # noqa: E402

cap = open_camera(camera_arg())
pose = HeadPose()
ema = Ema(alpha=0.3)
side = SideClassifier()
t0 = time.perf_counter()
COLORS = {"LEFT": (255, 160, 0), "RIGHT": (0, 160, 255), "UNKNOWN": (180, 180, 180)}

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
    raw = "-" if angles is None else f"{angles[0]:+6.1f}"
    smooth = "no face" if yaw is None else f"{yaw:+6.1f}"
    lines = [
        (f"{label}", COLORS[label], 1.4),
        (f"yaw raw {raw}  smooth {smooth}", (0, 255, 0), 0.7),
        (f"left ref {side.left if side.left is None else round(side.left, 1)}   "
         f"right ref {side.right if side.right is None else round(side.right, 1)}", (255, 255, 255), 0.7),
        ("L/R = record side, C = clear, Esc = quit", (255, 255, 255), 0.6),
    ]
    y = 35
    for text, color, scale in lines:
        cv2.putText(frame, text, (10, y), cv2.FONT_HERSHEY_SIMPLEX, scale, color, 2)
        y += int(35 * max(scale, 0.7))
    cv2.imshow("classifier", frame)

    key = cv2.waitKey(1) & 0xFF
    if key in (27, ord("q")):
        break
    if key == ord("l") and yaw is not None:
        side.left = yaw
    elif key == ord("r") and yaw is not None:
        side.right = yaw
    elif key == ord("c"):
        side.left = side.right = None

pose.close()
cap.release()
cv2.destroyAllWindows()

"""Step 3: live yaw/pitch/roll readout. Esc or q quits. Nothing is saved."""
import sys
import time
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from camera import camera_arg, open_camera  # noqa: E402
from headpose import HeadPose  # noqa: E402

cap = open_camera(camera_arg())

pose = HeadPose()
t0 = time.perf_counter()
while True:
    ok, frame = cap.read()
    if not ok:
        break
    ms = (time.perf_counter() - t0) * 1000
    angles = pose.estimate(frame, ms)
    frame = cv2.flip(frame, 1)
    if angles is None:
        lines, color = ["no face"], (0, 0, 255)
    else:
        yaw, pitch, roll = angles
        lines = [f"yaw   {yaw:+6.1f}", f"pitch {pitch:+6.1f}", f"roll  {roll:+6.1f}"]
        color = (0, 255, 0)
    for i, text in enumerate(lines):
        cv2.putText(frame, text, (10, 30 + 30 * i), cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2)
    cv2.imshow("head pose (Esc to quit)", frame)
    if cv2.waitKey(1) & 0xFF in (27, ord("q")):
        break

pose.close()
cap.release()
cv2.destroyAllWindows()

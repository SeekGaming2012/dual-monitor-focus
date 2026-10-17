"""Step 2: live webcam preview with fps. Esc or q quits. Nothing is saved."""
import sys
import time
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from camera import camera_arg, open_camera  # noqa: E402

cap = open_camera(camera_arg())

last, fps = time.perf_counter(), 0.0
while True:
    ok, frame = cap.read()
    if not ok:
        break
    now = time.perf_counter()
    fps = 0.9 * fps + 0.1 / max(now - last, 1e-6)
    last = now
    frame = cv2.flip(frame, 1)
    cv2.putText(frame, f"{fps:4.1f} fps  (Esc to quit)", (10, 25),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    cv2.imshow("preview", frame)
    if cv2.waitKey(1) & 0xFF in (27, ord("q")):
        break

cap.release()
cv2.destroyAllWindows()

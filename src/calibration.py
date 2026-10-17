"""Two-point calibration: look at the left monitor, then the right.

A fullscreen prompt appears on each monitor. After a short settling period, head
angles are sampled for a few seconds; the median is kept. Nothing but angles is stored.
"""
import statistics
import time

import cv2
import numpy as np

WINDOW = "calibration"
SETTLE_S = 1.5
SAMPLE_S = 2.5
MIN_SAMPLES = 15
MIN_SEPARATION_DEG = 10.0


class CalibrationAborted(Exception):
    pass


class CalibrationFailed(Exception):
    pass


def _show_on(monitor):
    cv2.namedWindow(WINDOW, cv2.WINDOW_NORMAL)
    cv2.moveWindow(WINDOW, monitor.left, monitor.top)
    cv2.resizeWindow(WINDOW, monitor.width, monitor.height)
    cv2.setWindowProperty(WINDOW, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)


def _prompt(monitor, title, subtitle, progress):
    img = np.full((monitor.height, monitor.width, 3), 24, np.uint8)
    cx, cy = monitor.width // 2, monitor.height // 2
    cv2.circle(img, (cx, cy), 22, (0, 200, 255), -1)
    cv2.circle(img, (cx, cy), 40, (0, 200, 255), 2)
    cv2.putText(img, title, (cx - 330, cy - 120), cv2.FONT_HERSHEY_SIMPLEX, 1.6, (255, 255, 255), 3)
    cv2.putText(img, subtitle, (cx - 330, cy + 120), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (200, 200, 200), 2)
    bar_w = 500
    cv2.rectangle(img, (cx - bar_w // 2, cy + 170), (cx + bar_w // 2, cy + 190), (80, 80, 80), 2)
    cv2.rectangle(img, (cx - bar_w // 2, cy + 170),
                  (cx - bar_w // 2 + int(bar_w * progress), cy + 190), (0, 200, 255), -1)
    cv2.imshow(WINDOW, img)


def _capture_side(cap, pose, monitor, label, t0):
    _show_on(monitor)
    yaws, pitches = [], []
    start = time.perf_counter()
    total = SETTLE_S + SAMPLE_S
    while True:
        elapsed = time.perf_counter() - start
        if elapsed >= total:
            break
        ok, frame = cap.read()
        if not ok:
            raise CalibrationFailed("Camera stopped delivering frames.")
        angles = pose.estimate(frame, (time.perf_counter() - t0) * 1000)
        settling = elapsed < SETTLE_S
        if angles is not None and not settling:
            yaws.append(angles[0])
            pitches.append(angles[1])
        status = "Get ready..." if settling else ("Hold still..." if angles else "Face not visible!")
        _prompt(monitor, f"Look at the {label} monitor", status, elapsed / total)
        if cv2.waitKey(1) & 0xFF == 27:
            raise CalibrationAborted()
    if len(yaws) < MIN_SAMPLES:
        raise CalibrationFailed(f"Only {len(yaws)} usable frames for the {label} side; is your face visible?")
    return {
        "yaw": statistics.median(yaws),
        "pitch": statistics.median(pitches),
        "yaw_std": statistics.pstdev(yaws),
        "samples": len(yaws),
    }


def run_calibration(cap, pose, monitors, camera_index):
    """Return a calibration dict. `monitors` must be sorted left to right (at least two)."""
    if len(monitors) < 2:
        raise CalibrationFailed("Two monitors are required.")
    left_mon, right_mon = monitors[0], monitors[-1]
    t0 = time.perf_counter()
    try:
        left = _capture_side(cap, pose, left_mon, "LEFT", t0)
        right = _capture_side(cap, pose, right_mon, "RIGHT", t0)
    finally:
        cv2.destroyWindow(WINDOW)
    separation = abs(left["yaw"] - right["yaw"])
    if separation < MIN_SEPARATION_DEG:
        raise CalibrationFailed(
            f"Left and right differ by only {separation:.1f} degrees; turn your head more clearly toward each monitor.")
    return {
        "left": left,
        "right": right,
        "separation": separation,
        "camera": camera_index,
        "monitors": [[m.left, m.top, m.right, m.bottom] for m in monitors],
        "created": time.strftime("%Y-%m-%d %H:%M:%S"),
    }

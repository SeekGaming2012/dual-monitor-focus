"""Camera opening shared by the step scripts."""
import argparse
import time

import cv2


def camera_arg():
    parser = argparse.ArgumentParser()
    parser.add_argument("--camera", type=int, default=0, help="camera index (see step0_list_cameras.py)")
    return parser.parse_args().camera


def open_camera(index, attempts=5, delay_s=1.0):
    """Open the camera and confirm it delivers a frame, retrying while it may still be releasing."""
    for attempt in range(attempts):
        cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
        if cap.isOpened():
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            ok, _ = cap.read()
            if ok:
                return cap
        cap.release()
        if attempt < attempts - 1:
            time.sleep(delay_s)
    raise SystemExit(
        f"Could not open camera {index} after {attempts} attempts. "
        "Another app may be using it (browser, Teams, Zoom, Camera app), or try another index "
        "(see step0_list_cameras.py).")

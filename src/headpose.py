"""Head pose (yaw/pitch/roll in degrees) from a webcam frame via MediaPipe."""
import math
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks.python import BaseOptions, vision

MODEL = Path(__file__).resolve().parent.parent / "models" / "face_landmarker.task"


class HeadPose:
    def __init__(self):
        options = vision.FaceLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=str(MODEL)),
            running_mode=vision.RunningMode.VIDEO,
            num_faces=1,
            output_facial_transformation_matrixes=True,
        )
        self._landmarker = vision.FaceLandmarker.create_from_options(options)
        self._last_ms = -1

    def estimate(self, frame_bgr, timestamp_ms):
        """Return (yaw, pitch, roll) in degrees, or None if no face is found.

        Positive yaw = head turned to the user's right (provisional; verified in step 3).
        """
        timestamp_ms = max(int(timestamp_ms), self._last_ms + 1)
        self._last_ms = timestamp_ms
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result = self._landmarker.detect_for_video(image, timestamp_ms)
        if not result.facial_transformation_matrixes:
            return None
        r = np.asarray(result.facial_transformation_matrixes[0])[:3, :3]
        yaw = math.degrees(math.asin(max(-1.0, min(1.0, -r[2, 0]))))
        pitch = math.degrees(math.atan2(r[2, 1], r[2, 2]))
        roll = math.degrees(math.atan2(r[1, 0], r[0, 0]))
        return yaw, pitch, roll

    def close(self):
        self._landmarker.close()

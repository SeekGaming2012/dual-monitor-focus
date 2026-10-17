"""Step 1: confirm the dependencies import and the face model is present."""
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np

MODEL = Path(__file__).resolve().parent.parent / "models" / "face_landmarker.task"

print("opencv   ", cv2.__version__)
print("mediapipe", mp.__version__)
print("numpy    ", np.__version__)
print("model    ", MODEL, "OK" if MODEL.exists() else "MISSING")

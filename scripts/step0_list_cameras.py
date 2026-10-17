"""List camera indices that open and the resolution each reports. Saves nothing."""
import cv2

for i in range(5):
    cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
    if cap.isOpened():
        ok, frame = cap.read()
        size = f"{frame.shape[1]}x{frame.shape[0]}" if ok else "no frame"
        print(f"camera {i}: opens, {size}")
    else:
        print(f"camera {i}: not available")
    cap.release()

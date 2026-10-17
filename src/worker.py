"""Background worker: camera -> head pose -> side -> dwell -> gate -> focus the window on that monitor.

Frames are processed in memory and discarded; nothing is saved or sent anywhere.
"""
import threading
import time

from camera import open_camera
from classify import Ema, SideClassifier
from dwell import DwellFilter
from focus import foreground_hwnd, focus_window
from headpose import HeadPose
from inputguard import SwitchGate
from monitors import list_monitors
from windows import process_name_of, topmost_window_on

RETRY_CAMERA_S = 2.0
PAUSED_POLL_S = 0.1
REOPEN_DELAY_S = 1.0   # pause before reopening a camera that failed, to avoid a tight retry loop
STALL_S = 3.0          # a longer gap between frames means sleep/wake or a hung camera
DARK_LEVEL = 10        # mean pixel value (0-255) below which the image is unusable
DARK_REPORT_S = 2.0
LAYOUT_CHECK_S = 2.0


def _layout(monitors):
    return [[m.left, m.top, m.right, m.bottom] for m in monitors]


class FocusWorker:
    def __init__(self, calibration, camera_index=0, settings=None, on_event=print):
        settings = settings or {}
        self._dwell_s = settings.get("dwell_s", 0.5)
        self._ignore_targets = tuple(settings.get("ignore_target_processes", ()))
        self._suspend_for = tuple(settings.get("suspend_when_foreground", ()))
        self._camera_index = camera_index
        self._on_event = on_event
        self.set_calibration(calibration)
        self._stop = threading.Event()
        self._running = threading.Event()  # set = active, cleared = paused
        self._running.set()
        self._camera_free = threading.Event()  # set whenever the worker does not hold the camera
        self._camera_free.set()
        self._thread = threading.Thread(target=self._run, name="focus-worker", daemon=True)

    def start(self):
        self._thread.start()

    def set_calibration(self, calibration):
        """Takes effect at the next session (pause then resume)."""
        self._side = SideClassifier(calibration["left"]["yaw"], calibration["right"]["yaw"])
        self._expected_layout = calibration.get("monitors")

    def set_camera(self, index):
        """Takes effect at the next session (pause then resume)."""
        self._camera_index = index

    def wait_camera_free(self, timeout=5.0):
        """After pause(): block until the camera has been released."""
        return self._camera_free.wait(timeout)

    def pause(self):
        self._running.clear()

    def resume(self):
        self._running.set()

    @property
    def paused(self):
        return not self._running.is_set()

    def stop(self):
        self._stop.set()
        self._running.set()  # wake a paused loop so it can exit
        self._thread.join(timeout=5)

    def _run(self):
        pose = HeadPose()
        try:
            while not self._stop.is_set():
                if not self._running.is_set():
                    self._running.wait(PAUSED_POLL_S)
                    continue
                self._session(pose)
        finally:
            pose.close()

    def _session(self, pose):
        """Run while active; returns when paused, stopped, the camera fails, or after a stall."""
        try:
            cap = open_camera(self._camera_index, attempts=1)
        except SystemExit:
            self._on_event(f"camera {self._camera_index} unavailable, retrying")
            self._stop.wait(RETRY_CAMERA_S)
            return
        self._camera_free.clear()
        self._on_event("tracking")
        ema = Ema(alpha=0.3)
        dwell = DwellFilter(dwell_s=self._dwell_s)
        gate = SwitchGate()
        side = self._side
        t0 = time.perf_counter()
        last_frame = 0.0
        dark_since = None
        dark_reported = False
        next_layout_check = 0.0
        layout_ok = True
        try:
            while self._running.is_set() and not self._stop.is_set():
                ok, frame = cap.read()
                if not ok:
                    self._on_event("camera stopped delivering frames")
                    self._stop.wait(REOPEN_DELAY_S)
                    return
                now = time.perf_counter() - t0
                if now - last_frame > STALL_S:
                    self._on_event("camera stalled (sleep/wake?), reopening")
                    self._stop.wait(REOPEN_DELAY_S)
                    return
                last_frame = now

                if now >= next_layout_check:
                    next_layout_check = now + LAYOUT_CHECK_S
                    layout_ok = self._check_layout(layout_ok)

                if frame[::8, ::8].mean() < DARK_LEVEL:
                    dark_since = dark_since if dark_since is not None else now
                    if not dark_reported and now - dark_since > DARK_REPORT_S:
                        dark_reported = True
                        self._on_event("too dark to see your face")
                    angles = None
                else:
                    if dark_reported:
                        self._on_event("tracking")
                    dark_since, dark_reported = None, False
                    angles = pose.estimate(frame, now * 1000)

                if angles is None:
                    ema.reset()
                    yaw = None
                else:
                    yaw = ema.update(angles[0])
                label = side.classify(yaw)
                switched = dwell.update(label, now)
                if switched and layout_ok:
                    gate.request(switched, now)
                ready = gate.tick(now, label)
                if ready and layout_ok:
                    self._focus(ready)
        finally:
            cap.release()
            self._camera_free.set()
            if self.paused:
                self._on_event("paused (camera released)")

    def _check_layout(self, was_ok):
        """Switching needs two monitors; a changed layout is reported once but does not block."""
        monitors = list_monitors()
        ok = len(monitors) >= 2
        if ok != was_ok:
            self._on_event("tracking" if ok else "need two monitors")
        if ok and self._expected_layout is not None and _layout(monitors) != self._expected_layout:
            self._expected_layout = _layout(monitors)
            self._on_event("monitor layout changed since calibration")
        return ok

    def _focus(self, side):
        fg = foreground_hwnd()
        if fg and process_name_of(fg) in self._suspend_for:
            self._on_event(f"{side}: skipped (foreground app is on the suspend list)")
            return
        monitors = list_monitors()
        monitor = monitors[0] if side == "LEFT" else monitors[-1]
        window = topmost_window_on(monitor, ignore_processes=self._ignore_targets)
        if window is None:
            self._on_event(f"{side}: no window on that monitor")
            return
        how = focus_window(window.hwnd)
        self._on_event(f"{side}: {window.process} -> {how or 'FAILED'}")

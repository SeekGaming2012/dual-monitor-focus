"""System tray app: status icon with Pause/Resume, Recalibrate and Quit."""
import ctypes
import logging
import threading
from logging.handlers import RotatingFileHandler

import cv2
import pystray
from PIL import Image, ImageDraw

import autostart
from calibration import CalibrationAborted, CalibrationFailed, run_calibration
from camera import open_camera
from config import CONFIG_DIR, load_calibration, save_calibration
from headpose import HeadPose
from monitors import enable_dpi_awareness, list_monitors
from settings import load_settings
from worker import FocusWorker

MUTEX_NAME = "Local\\DualMonitorFocusSingleInstance"
ERROR_ALREADY_EXISTS = 183
STATE_COLORS = {"active": (60, 200, 90), "paused": (140, 140, 140), "problem": (230, 170, 40)}

log = logging.getLogger("dual-monitor-focus")


def _setup_logging():
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(CONFIG_DIR / "app.log", maxBytes=200_000, backupCount=1, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(message)s", "%H:%M:%S"))
    log.addHandler(handler)
    log.setLevel(logging.INFO)


def _already_running():
    ctypes.windll.kernel32.CreateMutexW(None, False, MUTEX_NAME)
    return ctypes.windll.kernel32.GetLastError() == ERROR_ALREADY_EXISTS


def _message_box(text):
    ctypes.windll.user32.MessageBoxW(None, text, "Dual Monitor Focus", 0x40)


def make_icon(state):
    """Two small monitors side by side; the color shows the state."""
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    color = STATE_COLORS[state]
    d.rounded_rectangle((2, 14, 30, 44), radius=4, fill=color)
    d.rounded_rectangle((34, 14, 62, 44), radius=4, fill=color)
    d.rectangle((12, 48, 20, 52), fill=color)
    d.rectangle((44, 48, 52, 52), fill=color)
    d.ellipse((24, 24, 40, 40), fill=(20, 20, 20, 255), outline=(255, 255, 255, 255), width=2)
    return img


def calibrate_blocking(camera_index):
    """Run the two-point calibration with its own camera. Returns the calibration or None."""
    enable_dpi_awareness()
    cap = pose = None
    try:
        cap = open_camera(camera_index)
        pose = HeadPose()
        cal = run_calibration(cap, pose, list_monitors(), camera_index)
        save_calibration(cal)
        return cal
    except (CalibrationAborted, CalibrationFailed, SystemExit) as e:
        log.info("calibration did not complete: %s", e or "aborted")
        return None
    finally:
        if pose:
            pose.close()
        if cap:
            cap.release()
        cv2.destroyAllWindows()


class TrayApp:
    def __init__(self, calibration, settings=None):
        self._camera = calibration.get("camera", 0)
        self._status = "starting"
        self._calibrating = False
        self._worker = FocusWorker(calibration, camera_index=self._camera, settings=settings,
                                   on_event=self._on_event)
        self._icon = pystray.Icon(
            "dual-monitor-focus", make_icon("active"), "Dual Monitor Focus",
            menu=pystray.Menu(
                pystray.MenuItem(lambda item: f"Status: {self._status}", None, enabled=False),
                pystray.MenuItem(lambda item: "Resume tracking" if self._worker.paused else "Pause tracking",
                                 self._toggle_pause, default=True),
                pystray.MenuItem("Recalibrate...", self._recalibrate, enabled=lambda item: not self._calibrating),
                pystray.MenuItem("Start with Windows", self._toggle_autostart,
                                 checked=lambda item: autostart.is_enabled()),
                pystray.MenuItem("Quit", self._quit),
            ))

    def run(self):
        self._icon.run(setup=self._setup)

    def _setup(self, icon):
        icon.visible = True
        self._worker.start()

    def _on_event(self, message):
        log.info(message)
        if message == "tracking":
            self._set_state("active", "tracking")
        elif message.startswith("paused"):
            self._set_state("paused", "paused")
        elif "unavailable" in message or "stopped delivering" in message or "stalled" in message:
            self._set_state("problem", "camera unavailable, retrying")
        elif message.startswith("too dark"):
            self._set_state("problem", "too dark to see your face")
        elif message.startswith("need two monitors"):
            self._set_state("problem", "needs two monitors")
        elif message.startswith("monitor layout changed"):
            try:
                self._icon.notify("Monitor layout changed. If switching feels off, choose Recalibrate.",
                                  "Dual Monitor Focus")
            except Exception:  # notifications are best-effort
                pass

    def _set_state(self, state, status):
        self._status = status
        self._icon.icon = make_icon(state)
        self._icon.title = f"Dual Monitor Focus: {status}"
        self._icon.update_menu()

    def _toggle_pause(self, icon=None, item=None):
        if self._worker.paused:
            self._worker.resume()
        else:
            self._worker.pause()
            self._set_state("paused", "paused")

    def _toggle_autostart(self, icon=None, item=None):
        try:
            if autostart.is_enabled():
                autostart.disable()
                log.info("start with Windows: off")
            else:
                autostart.enable()
                log.info("start with Windows: on")
        except OSError as e:
            log.info("could not change start with Windows: %s", e)
            try:
                self._icon.notify(f"Could not change the startup setting: {e}", "Dual Monitor Focus")
            except Exception:  # notifications are best-effort
                pass
        self._icon.update_menu()

    def _recalibrate(self, icon=None, item=None):
        if self._calibrating:
            return
        self._calibrating = True
        threading.Thread(target=self._recalibrate_task, name="recalibrate", daemon=True).start()

    def _recalibrate_task(self):
        try:
            self._worker.pause()
            self._set_state("paused", "calibrating")
            if not self._worker.wait_camera_free():
                log.info("camera did not release in time; skipping calibration")
                return
            cal = calibrate_blocking(self._camera)
            if cal is not None:
                self._worker.set_calibration(cal)
        finally:
            self._calibrating = False
            self._worker.resume()

    def _quit(self, icon=None, item=None):
        self._worker.stop()
        self._icon.stop()


def main():
    _setup_logging()
    if _already_running():
        log.info("another instance is already running; exiting")
        _message_box("Dual Monitor Focus is already running (check the tray).")
        return
    cal = load_calibration()
    if cal is None:
        log.info("no calibration found; calibrating")
        cal = calibrate_blocking(0)
        if cal is None:
            _message_box("Calibration was not completed, so the app will exit. Start it again to retry.")
            return
    TrayApp(cal, load_settings()).run()

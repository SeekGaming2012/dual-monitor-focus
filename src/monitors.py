"""Monitor discovery via the Win32 API (ctypes, no extra dependencies)."""
import ctypes
from ctypes import wintypes
from dataclasses import dataclass

user32 = ctypes.windll.user32


def enable_dpi_awareness():
    """Make coordinates physical pixels. Call once, before creating any windows."""
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # per-monitor
    except (AttributeError, OSError):
        user32.SetProcessDPIAware()


@dataclass(frozen=True)
class Monitor:
    left: int
    top: int
    right: int
    bottom: int
    primary: bool

    @property
    def width(self):
        return self.right - self.left

    @property
    def height(self):
        return self.bottom - self.top


class _MONITORINFO(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.DWORD), ("rcMonitor", wintypes.RECT),
                ("rcWork", wintypes.RECT), ("dwFlags", wintypes.DWORD)]


def list_monitors():
    """All monitors, sorted left to right."""
    found = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HMONITOR, wintypes.HDC,
                        ctypes.POINTER(wintypes.RECT), wintypes.LPARAM)
    def callback(hmon, _hdc, _rect, _data):
        info = _MONITORINFO()
        info.cbSize = ctypes.sizeof(info)
        user32.GetMonitorInfoW(hmon, ctypes.byref(info))
        r = info.rcMonitor
        found.append(Monitor(r.left, r.top, r.right, r.bottom, bool(info.dwFlags & 1)))
        return True

    user32.EnumDisplayMonitors(None, None, callback, 0)
    return sorted(found, key=lambda m: m.left)

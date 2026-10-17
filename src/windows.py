"""Find the topmost usable window on a monitor (ctypes, no extra dependencies)."""
import ctypes
import os
from ctypes import wintypes
from dataclasses import dataclass

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
dwmapi = ctypes.windll.dwmapi

user32.IsWindowVisible.argtypes = [wintypes.HWND]
user32.IsIconic.argtypes = [wintypes.HWND]
user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
kernel32.OpenProcess.restype = wintypes.HANDLE
kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
kernel32.QueryFullProcessImageNameW.argtypes = [
    wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
dwmapi.DwmGetWindowAttribute.argtypes = [wintypes.HWND, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD]

GWL_EXSTYLE = -20
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_NOACTIVATE = 0x08000000
WS_EX_APPWINDOW = 0x00040000
DWMWA_CLOAKED = 14
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000

# Shell surfaces that are never a sensible focus target.
IGNORED_CLASSES = {"Progman", "WorkerW", "Shell_TrayWnd", "Shell_SecondaryTrayWnd", "NotifyIconOverflowWindow"}


@dataclass(frozen=True)
class WindowInfo:
    hwnd: int
    title: str
    cls: str
    process: str


def _text(hwnd):
    n = user32.GetWindowTextLengthW(hwnd)
    buf = ctypes.create_unicode_buffer(n + 1)
    user32.GetWindowTextW(hwnd, buf, n + 1)
    return buf.value


def _class(hwnd):
    buf = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(hwnd, buf, 256)
    return buf.value


def _process_name(hwnd):
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid.value)
    if not handle:
        return "?"
    try:
        buf = ctypes.create_unicode_buffer(1024)
        size = wintypes.DWORD(1024)
        if kernel32.QueryFullProcessImageNameW(handle, 0, buf, ctypes.byref(size)):
            return os.path.basename(buf.value)
        return "?"
    finally:
        kernel32.CloseHandle(handle)


def _is_cloaked(hwnd):
    """True for windows on other virtual desktops or hidden UWP shells."""
    cloaked = wintypes.DWORD(0)
    dwmapi.DwmGetWindowAttribute(hwnd, DWMWA_CLOAKED, ctypes.byref(cloaked), ctypes.sizeof(cloaked))
    return bool(cloaked.value)


def _is_candidate(hwnd, own_pid):
    if not user32.IsWindowVisible(hwnd) or user32.IsIconic(hwnd) or _is_cloaked(hwnd):
        return False
    ex = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
    if ex & WS_EX_NOACTIVATE:
        return False
    if (ex & WS_EX_TOOLWINDOW) and not (ex & WS_EX_APPWINDOW):
        return False
    if _class(hwnd) in IGNORED_CLASSES or not _text(hwnd):
        return False
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return pid.value != own_pid


def _center_in(hwnd, monitor):
    rect = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    cx, cy = (rect.left + rect.right) // 2, (rect.top + rect.bottom) // 2
    return monitor.left <= cx < monitor.right and monitor.top <= cy < monitor.bottom


def windows_by_zorder():
    """All top-level window handles, topmost first."""
    handles = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def callback(hwnd, _):
        handles.append(hwnd)
        return True

    user32.EnumWindows(callback, 0)
    return handles


def process_name_of(hwnd):
    """Executable name (e.g. "chrome.exe") of the window's process, lowercased, or "?"."""
    return _process_name(hwnd).lower()


def topmost_window_on(monitor, exclude_own_process=True, ignore_processes=()):
    """The frontmost usable window whose center lies on `monitor`, or None.

    `ignore_processes` are lowercase executable names that are never returned.
    """
    own_pid = os.getpid() if exclude_own_process else -1
    for hwnd in windows_by_zorder():
        if not (_is_candidate(hwnd, own_pid) and _center_in(hwnd, monitor)):
            continue
        process = _process_name(hwnd)
        if process.lower() in ignore_processes:
            continue
        return WindowInfo(hwnd, _text(hwnd), _class(hwnd), process)
    return None

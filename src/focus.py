"""Bring a window to the foreground from a background process.

Windows blocks SetForegroundWindow unless the caller recently received input. Two standard
workarounds are tried in order, no admin rights needed:
  1. tap Alt (counts as input), then SetForegroundWindow
  2. attach our input queue to the current foreground thread, then SetForegroundWindow
Windows of elevated apps still cannot be focused from a non-elevated process.
"""
import ctypes
import time
from ctypes import wintypes

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

user32.GetForegroundWindow.restype = wintypes.HWND
user32.SetForegroundWindow.argtypes = [wintypes.HWND]
user32.BringWindowToTop.argtypes = [wintypes.HWND]
user32.SetFocus.argtypes = [wintypes.HWND]
user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
user32.IsIconic.argtypes = [wintypes.HWND]
user32.IsWindow.argtypes = [wintypes.HWND]
user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
user32.AttachThreadInput.argtypes = [wintypes.DWORD, wintypes.DWORD, wintypes.BOOL]

SW_RESTORE = 9
VK_MENU = 0x12  # Alt
KEYEVENTF_KEYUP = 0x0002
VERIFY_TIMEOUT_S = 0.25


def foreground_hwnd():
    return user32.GetForegroundWindow()


def _wait_foreground(hwnd, timeout_s=VERIFY_TIMEOUT_S):
    """Poll briefly: the switch is not always visible to GetForegroundWindow immediately."""
    end = time.perf_counter() + timeout_s
    while True:
        if foreground_hwnd() == hwnd:
            return True
        if time.perf_counter() >= end:
            return False
        time.sleep(0.01)


def _alt_tap_method(hwnd):
    user32.keybd_event(VK_MENU, 0, 0, 0)
    user32.keybd_event(VK_MENU, 0, KEYEVENTF_KEYUP, 0)
    user32.SetForegroundWindow(hwnd)


def _attach_method(hwnd):
    fg = foreground_hwnd()
    fg_thread = user32.GetWindowThreadProcessId(fg, None) if fg else 0
    target_thread = user32.GetWindowThreadProcessId(hwnd, None)
    our_thread = kernel32.GetCurrentThreadId()
    attached = []
    for other in {fg_thread, target_thread} - {0, our_thread}:
        if user32.AttachThreadInput(our_thread, other, True):
            attached.append(other)
    try:
        user32.BringWindowToTop(hwnd)
        user32.SetForegroundWindow(hwnd)
        user32.SetFocus(hwnd)
    finally:
        for other in attached:
            user32.AttachThreadInput(our_thread, other, False)


def focus_window(hwnd):
    """Try to give `hwnd` keyboard focus. Returns the method that worked, or None.

    Returns "already" if the window already had focus.
    """
    if not user32.IsWindow(hwnd):
        return None
    if foreground_hwnd() == hwnd:
        return "already"
    if user32.IsIconic(hwnd):
        user32.ShowWindow(hwnd, SW_RESTORE)
    for name, method in (("alt-tap", _alt_tap_method), ("attach", _attach_method)):
        method(hwnd)
        if _wait_foreground(hwnd):
            return name
    return None

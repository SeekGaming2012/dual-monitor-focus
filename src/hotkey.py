"""Global keyboard shortcut via RegisterHotKey.

Windows delivers only the exact combination you register; the app never sees any other
keystrokes (this is not a keyboard hook).
"""
import ctypes
import threading
from ctypes import wintypes

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

user32.RegisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT]
user32.UnregisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int]
user32.GetMessageW.argtypes = [ctypes.POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT]
user32.PeekMessageW.argtypes = [ctypes.POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT,
                                wintypes.UINT]
user32.PostThreadMessageW.argtypes = [wintypes.DWORD, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]

MOD_ALT, MOD_CONTROL, MOD_SHIFT, MOD_WIN, MOD_NOREPEAT = 0x1, 0x2, 0x4, 0x8, 0x4000
WM_HOTKEY, WM_QUIT = 0x0312, 0x0012
ERROR_HOTKEY_ALREADY_REGISTERED = 1409
HOTKEY_ID = 1

_MODIFIERS = {"ctrl": MOD_CONTROL, "control": MOD_CONTROL, "alt": MOD_ALT, "shift": MOD_SHIFT,
              "win": MOD_WIN}
_NAMED_KEYS = {"space": 0x20, "pause": 0x13, "insert": 0x2D, "delete": 0x2E, "home": 0x24, "end": 0x23,
               "pageup": 0x21, "pagedown": 0x22, "up": 0x26, "down": 0x28, "left": 0x25, "right": 0x27,
               "scrolllock": 0x91, "printscreen": 0x2C}


def parse_hotkey(text):
    """"ctrl+alt+p" -> (modifier_flags, virtual_key). Raises ValueError if unusable."""
    parts = [p.strip().lower() for p in text.split("+") if p.strip()]
    if len(parts) < 2:
        raise ValueError(f"hotkey {text!r} needs at least one modifier and a key, e.g. ctrl+alt+p")
    *mods, key = parts
    flags = 0
    for m in mods:
        if m not in _MODIFIERS:
            raise ValueError(f"unknown modifier {m!r} in hotkey {text!r} (use ctrl, alt, shift, win)")
        flags |= _MODIFIERS[m]
    if len(key) == 1 and key.isalnum():
        vk = ord(key.upper())
    elif key.startswith("f") and key[1:].isdigit() and 1 <= int(key[1:]) <= 24:
        vk = 0x70 + int(key[1:]) - 1
    elif key in _NAMED_KEYS:
        vk = _NAMED_KEYS[key]
    else:
        raise ValueError(f"unknown key {key!r} in hotkey {text!r}")
    return flags, vk


def display_name(text):
    """"ctrl+alt+p" -> "Ctrl+Alt+P" """
    return "+".join(p.strip().capitalize() if len(p.strip()) > 1 else p.strip().upper()
                    for p in text.split("+"))


class HotkeyListener:
    """Registers the shortcut on its own thread and calls `callback()` each time it is pressed."""

    def __init__(self, text, callback, on_error=print):
        self._text = text
        self._callback = callback
        self._on_error = on_error
        self._thread = threading.Thread(target=self._run, name="hotkey", daemon=True)
        self._thread_id = None
        self._started = threading.Event()
        self.registered = False

    def start(self):
        self._thread.start()
        self._started.wait(2)
        return self.registered

    def stop(self):
        if self._thread_id is not None:
            user32.PostThreadMessageW(self._thread_id, WM_QUIT, 0, 0)
        self._thread.join(timeout=2)

    def _run(self):
        self._thread_id = kernel32.GetCurrentThreadId()
        msg = wintypes.MSG()
        user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, 0)  # create this thread's message queue
        try:
            flags, vk = parse_hotkey(self._text)
        except ValueError as e:
            self._on_error(str(e))
            self._started.set()
            return
        if user32.RegisterHotKey(None, HOTKEY_ID, flags | MOD_NOREPEAT, vk):
            self.registered = True
        else:
            reason = ("already used by another program"
                      if ctypes.get_last_error() == ERROR_HOTKEY_ALREADY_REGISTERED or
                      kernel32.GetLastError() == ERROR_HOTKEY_ALREADY_REGISTERED else "registration failed")
            self._on_error(f"hotkey {self._text!r} could not be registered: {reason}")
        self._started.set()
        if not self.registered:
            return
        try:
            while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
                if msg.message == WM_HOTKEY:
                    self._callback()
        finally:
            user32.UnregisterHotKey(None, HOTKEY_ID)

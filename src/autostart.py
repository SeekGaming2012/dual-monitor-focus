"""Start with Windows, via the per-user Run registry key (no admin rights needed)."""
import sys
import winreg
from pathlib import Path

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
# Windows records "turned off in Settings > Startup apps" here; first byte odd = disabled.
APPROVED_KEY = r"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run"
VALUE_NAME = "DualMonitorFocus"
MAIN_PY = Path(__file__).resolve().parent.parent / "main.py"


def command_line():
    """pythonw.exe (no console window) + main.py, with absolute paths."""
    exe = Path(sys.executable)
    pythonw = exe.with_name("pythonw.exe")
    return f'"{pythonw if pythonw.exists() else exe}" "{MAIN_PY}"'


def _read(key_path, name):
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path) as key:
            return winreg.QueryValueEx(key, name)[0]
    except FileNotFoundError:
        return None


def is_enabled():
    """True only if the entry points at this installation and Windows hasn't disabled it."""
    if _read(RUN_KEY, VALUE_NAME) != command_line():
        return False
    approved = _read(APPROVED_KEY, VALUE_NAME)
    return not (isinstance(approved, bytes) and approved and approved[0] & 1)


def enable():
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
        winreg.SetValueEx(key, VALUE_NAME, 0, winreg.REG_SZ, command_line())
    try:  # clear a previous "disabled in Settings" mark so the entry is honored again
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, APPROVED_KEY, 0, winreg.KEY_SET_VALUE) as key:
            winreg.DeleteValue(key, VALUE_NAME)
    except FileNotFoundError:
        pass


def disable():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
            winreg.DeleteValue(key, VALUE_NAME)
    except FileNotFoundError:
        pass

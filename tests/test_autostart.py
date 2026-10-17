import sys
import winreg
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
import autostart  # noqa: E402

TEST_ROOT = r"Software\DualMonitorFocusTest"


@pytest.fixture(autouse=True)
def temp_keys(monkeypatch):
    """Point the module at a throwaway registry area, never the real Run key."""
    monkeypatch.setattr(autostart, "RUN_KEY", TEST_ROOT + r"\Run")
    monkeypatch.setattr(autostart, "APPROVED_KEY", TEST_ROOT + r"\Approved")
    yield
    for sub in (r"\Run", r"\Approved", ""):
        try:
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, TEST_ROOT + sub)
        except FileNotFoundError:
            pass


def test_disabled_by_default():
    assert not autostart.is_enabled()


def test_enable_then_disable():
    autostart.enable()
    assert autostart.is_enabled()
    autostart.disable()
    assert not autostart.is_enabled()


def test_disable_when_not_enabled_is_harmless():
    autostart.disable()
    assert not autostart.is_enabled()


def test_command_uses_pythonw_and_absolute_main_py():
    cmd = autostart.command_line()
    assert cmd.startswith('"') and "pythonw.exe" in cmd.lower()
    assert str(autostart.MAIN_PY) in cmd and autostart.MAIN_PY.is_absolute()


def test_entry_for_another_location_counts_as_not_enabled():
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, autostart.RUN_KEY) as key:
        winreg.SetValueEx(key, autostart.VALUE_NAME, 0, winreg.REG_SZ, r'"D:\old\pythonw.exe" "D:\old\main.py"')
    assert not autostart.is_enabled()
    autostart.enable()  # re-enabling repairs the stale path
    assert autostart.is_enabled()


def test_disabled_in_windows_settings_is_respected_and_enable_clears_it():
    autostart.enable()
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, autostart.APPROVED_KEY) as key:
        winreg.SetValueEx(key, autostart.VALUE_NAME, 0, winreg.REG_BINARY, bytes([3] + [0] * 11))
    assert not autostart.is_enabled()
    autostart.enable()
    assert autostart.is_enabled()

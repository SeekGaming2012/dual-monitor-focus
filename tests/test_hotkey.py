import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from hotkey import MOD_ALT, MOD_CONTROL, MOD_SHIFT, MOD_WIN, display_name, parse_hotkey  # noqa: E402


def test_letter_with_two_modifiers():
    assert parse_hotkey("ctrl+alt+p") == (MOD_CONTROL | MOD_ALT, ord("P"))


def test_case_and_spaces_are_ignored():
    assert parse_hotkey(" Ctrl + SHIFT + k ") == (MOD_CONTROL | MOD_SHIFT, ord("K"))


def test_function_keys():
    assert parse_hotkey("win+f9") == (MOD_WIN, 0x78)
    assert parse_hotkey("ctrl+alt+shift+f24") == (MOD_CONTROL | MOD_ALT | MOD_SHIFT, 0x87)


def test_named_keys_and_digits():
    assert parse_hotkey("ctrl+alt+pause") == (MOD_CONTROL | MOD_ALT, 0x13)
    assert parse_hotkey("ctrl+alt+5") == (MOD_CONTROL | MOD_ALT, ord("5"))


@pytest.mark.parametrize("bad", ["p", "", "ctrl", "ctrl+alt+", "hyper+p", "ctrl+f25", "ctrl+banana"])
def test_unusable_hotkeys_are_rejected(bad):
    with pytest.raises(ValueError):
        parse_hotkey(bad)


def test_display_name():
    assert display_name("ctrl+alt+p") == "Ctrl+Alt+P"
    assert display_name("ctrl+alt+f9") == "Ctrl+Alt+F9"

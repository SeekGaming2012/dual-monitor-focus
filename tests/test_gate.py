import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from inputguard import SwitchGate  # noqa: E402


class Keys:
    def __init__(self):
        self.down = False

    def __call__(self):
        return self.down


def make(**kw):
    keys = Keys()
    return keys, SwitchGate(busy_fn=keys, **kw)


def test_switches_immediately_when_idle():
    keys, g = make()
    g.request("RIGHT", 0.0)
    assert g.tick(0.0, "RIGHT") == "RIGHT"
    assert g.pending is None


def test_waits_while_key_held_then_quiet_period():
    keys, g = make(quiet_s=0.35)
    keys.down = True
    g.request("LEFT", 0.0)
    assert g.tick(0.1, "LEFT") is None
    keys.down = False
    assert g.tick(0.2, "LEFT") is None   # only 0.1 s since last key
    assert g.tick(0.5, "LEFT") == "LEFT"  # 0.4 s quiet


def test_gaps_between_keystrokes_do_not_release():
    keys, g = make(quiet_s=0.35)
    g.request("LEFT", 0.0)
    keys.down = True
    g.tick(0.0, "LEFT")
    keys.down = False
    assert g.tick(0.1, "LEFT") is None
    keys.down = True
    assert g.tick(0.2, "LEFT") is None
    keys.down = False
    assert g.tick(0.3, "LEFT") is None
    assert g.tick(0.6, "LEFT") == "LEFT"


def test_typing_before_request_is_remembered():
    keys, g = make(quiet_s=0.35)
    keys.down = True
    g.tick(1.0, "UNKNOWN")  # typing observed with nothing pending
    keys.down = False
    g.request("RIGHT", 1.1)
    assert g.tick(1.1, "RIGHT") is None  # typed 0.1 s ago
    assert g.tick(1.5, "RIGHT") == "RIGHT"


def test_looking_at_opposite_side_cancels():
    keys, g = make()
    keys.down = True
    g.request("LEFT", 0.0)
    g.tick(0.1, "LEFT")
    assert g.tick(0.2, "RIGHT") is None
    keys.down = False
    assert g.tick(2.0, "LEFT") is None  # nothing pending any more


def test_looking_down_keeps_pending():
    keys, g = make(quiet_s=0.35)
    keys.down = True
    g.request("LEFT", 0.0)
    g.tick(0.1, "UNKNOWN")
    keys.down = False
    assert g.tick(1.0, "UNKNOWN") == "LEFT"


def test_expires_after_max_wait():
    keys, g = make(max_wait_s=8.0)
    keys.down = True
    g.request("LEFT", 0.0)
    assert g.tick(9.0, "LEFT") is None
    keys.down = False
    assert g.tick(10.0, "LEFT") is None

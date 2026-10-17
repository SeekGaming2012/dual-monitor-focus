import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from dwell import DwellFilter  # noqa: E402


def feed(f, samples, fps=30):
    """samples: list of labels, one per frame. Returns list of (time, committed) events."""
    events = []
    for i, label in enumerate(samples):
        t = i / fps
        out = f.update(label, t)
        if out:
            events.append((round(t, 3), out))
    return events


def test_commits_after_dwell():
    f = DwellFilter(dwell_s=0.4)
    events = feed(f, ["RIGHT"] * 30)
    assert len(events) == 1
    assert events[0][1] == "RIGHT"
    assert 0.4 <= events[0][0] < 0.5


def test_brief_glance_does_not_commit():
    f = DwellFilter(dwell_s=0.4)
    assert feed(f, ["RIGHT"] * 8) == []  # ~0.27 s
    assert f.committed is None


def test_flicker_never_commits():
    f = DwellFilter(dwell_s=0.4)
    assert feed(f, ["LEFT", "RIGHT"] * 30) == []


def test_unknown_resets_candidate():
    f = DwellFilter(dwell_s=0.4)
    samples = ["LEFT"] * 10 + ["UNKNOWN"] + ["LEFT"] * 10  # each run ~0.33 s
    assert feed(f, samples) == []


def test_looking_away_keeps_committed_side():
    f = DwellFilter(dwell_s=0.4)
    feed(f, ["LEFT"] * 20)
    assert f.committed == "LEFT"
    assert feed(f, [None] * 60) == []
    assert f.committed == "LEFT"


def test_no_repeat_events_while_holding():
    f = DwellFilter(dwell_s=0.4)
    assert len(feed(f, ["LEFT"] * 90)) == 1


def test_switch_sides_after_dwell():
    f = DwellFilter(dwell_s=0.4)
    events = feed(f, ["LEFT"] * 20 + ["RIGHT"] * 20)
    assert [e[1] for e in events] == ["LEFT", "RIGHT"]


def test_return_to_committed_side_cancels_pending_switch():
    f = DwellFilter(dwell_s=0.4)
    feed(f, ["LEFT"] * 20)
    assert feed(f, ["RIGHT"] * 8 + ["LEFT"] * 5 + ["RIGHT"] * 8) == []
    assert f.committed == "LEFT"


def test_camera_stall_cancels_candidate():
    f = DwellFilter(dwell_s=0.4, max_gap_s=0.3)
    f.update("RIGHT", 0.0)
    f.update("RIGHT", 0.2)
    assert f.update("RIGHT", 1.0) is None  # long gap restarts the count
    assert f.update("RIGHT", 1.2) is None
    assert f.update("RIGHT", 1.45) == "RIGHT"


def test_progress_reports_fraction():
    f = DwellFilter(dwell_s=0.4)
    f.update("LEFT", 0.0)
    f.update("LEFT", 0.2)
    assert abs(f.progress - 0.5) < 1e-9
    assert f.candidate == "LEFT"

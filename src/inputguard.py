"""Defer focus switches while the user is typing or holding a mouse button."""
import ctypes

user32 = ctypes.windll.user32
user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
user32.GetAsyncKeyState.restype = ctypes.c_short

# Mouse buttons (1-6) and every keyboard virtual key from Backspace up.
_WATCHED_KEYS = (1, 2, 4, 5, 6) + tuple(range(0x08, 0xFF))


def input_busy():
    """True while any key or mouse button is physically held down."""
    return any(user32.GetAsyncKeyState(vk) & 0x8000 for vk in _WATCHED_KEYS)


class SwitchGate:
    """Holds a requested switch until input has been quiet for `quiet_s`.

    Call tick() every frame so typing is observed even when no switch is pending.
    A pending switch is dropped if you now look at the opposite monitor, or after `max_wait_s`.
    """

    def __init__(self, busy_fn=input_busy, quiet_s=0.35, max_wait_s=8.0):
        self._busy = busy_fn
        self.quiet_s = quiet_s
        self.max_wait_s = max_wait_s
        self._last_busy = None
        self._pending = None  # (side, requested_at)

    @property
    def pending(self):
        return self._pending[0] if self._pending else None

    def request(self, side, t):
        self._pending = (side, t)

    def tick(self, t, current_label):
        """Returns the side to switch to now, or None."""
        if self._busy():
            self._last_busy = t
        if self._pending is None:
            return None
        side, requested = self._pending
        opposite = "RIGHT" if side == "LEFT" else "LEFT"
        if current_label == opposite or t - requested > self.max_wait_s:
            self._pending = None
            return None
        if self._last_busy is not None and t - self._last_busy < self.quiet_s:
            return None
        self._pending = None
        return side

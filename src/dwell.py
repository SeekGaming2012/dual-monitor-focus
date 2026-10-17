"""Dwell filter: commit to LEFT/RIGHT only after a sustained look. Pure logic, time passed in."""


class DwellFilter:
    """Turns a noisy per-frame label stream into occasional committed switches.

    - A candidate side (LEFT or RIGHT) must be seen continuously for `dwell_s` to commit.
    - UNKNOWN or a missing face cancels the candidate but keeps the committed side
      (looking away never changes focus).
    - A gap longer than `max_gap_s` between samples (camera stall) also cancels it.
    """

    def __init__(self, dwell_s=0.5, max_gap_s=0.3):
        self.dwell_s = dwell_s
        self.max_gap_s = max_gap_s
        self.committed = None
        self._candidate = None
        self._since = None
        self._last_t = None

    @property
    def progress(self):
        """0..1 progress of the current candidate toward committing (for display)."""
        if self._candidate is None or self._since is None or self._last_t is None:
            return 0.0
        return min(1.0, (self._last_t - self._since) / self.dwell_s)

    @property
    def candidate(self):
        return self._candidate

    def update(self, label, t):
        """Feed one sample. Returns the newly committed side when it changes, else None."""
        if self._last_t is not None and t - self._last_t > self.max_gap_s:
            self._cancel()
        self._last_t = t

        if label not in ("LEFT", "RIGHT"):
            self._cancel()
            return None
        if label == self.committed:
            self._cancel()
            return None
        if label != self._candidate:
            self._candidate, self._since = label, t
        if t - self._since >= self.dwell_s:
            self.committed = label
            self._cancel()
            return label
        return None

    def _cancel(self):
        self._candidate = None
        self._since = None

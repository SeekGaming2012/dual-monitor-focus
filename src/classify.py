"""Smoothing and left/right classification from head yaw. Pure logic, no I/O."""


class Ema:
    def __init__(self, alpha=0.3):
        self.alpha = alpha
        self.value = None

    def update(self, x):
        self.value = x if self.value is None else self.alpha * x + (1 - self.alpha) * self.value
        return self.value

    def reset(self):
        self.value = None


class SideClassifier:
    """Midpoint between the left and right reference yaws, with a dead zone around it.

    Works whichever way the yaw sign runs: `left` and `right` are just recorded values.
    """

    def __init__(self, left=None, right=None, dead_fraction=0.15):
        self.left = left
        self.right = right
        self.dead_fraction = dead_fraction

    @property
    def ready(self):
        return self.left is not None and self.right is not None and self.left != self.right

    def classify(self, yaw):
        if yaw is None or not self.ready:
            return "UNKNOWN"
        mid = (self.left + self.right) / 2
        half_dead = abs(self.right - self.left) * self.dead_fraction
        toward_right = self.right > self.left
        if abs(yaw - mid) <= half_dead:
            return "UNKNOWN"
        return "RIGHT" if (yaw > mid) == toward_right else "LEFT"

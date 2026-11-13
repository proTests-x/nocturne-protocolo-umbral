"""Infinite rounds with bounded simultaneous and per-round enemy counts."""


class WaveManager:
    def __init__(self):
        self.round = 0
        self.remaining = 0
        self.intermission = 2.0
        self.active = False

    @staticmethod
    def count_for_round(round_number):
        if round_number <= 1:
            return 5
        if round_number == 2:
            return 8
        return min(90, 12 + (round_number - 3) * 4)

    def update(self, dt):
        """Return True exactly once when the next round should be enqueued."""
        if self.active:
            return False
        self.intermission = max(0.0, self.intermission - dt)
        if self.intermission > 0.0:
            return False
        self.round += 1
        self.remaining = self.count_for_round(self.round)
        self.active = True
        return True

    def on_kill(self):
        self.remaining = max(0, self.remaining - 1)

    def complete(self):
        self.active = False
        self.intermission = 5.0

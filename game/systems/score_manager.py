"""Combo scoring with explicit time windows and deterministic rewards."""


class ScoreManager:
    COMBO_WINDOW = 3.5
    MULTIKILL_WINDOW = 1.8

    def __init__(self):
        self.points = 0
        self.combo = 1.0
        self.streak = 0
        self.kills = 0
        self.headshots = 0
        self.timer = 0.0
        self.multi_timer = 0.0
        self.multi_count = 0
        self.last_award = 0

    def update(self, dt):
        self.timer = max(0.0, self.timer - dt)
        self.multi_timer = max(0.0, self.multi_timer - dt)
        if self.timer == 0.0:
            self.streak = 0
            self.combo = 1.0
        if self.multi_timer == 0.0:
            self.multi_count = 0

    def record_kill(self, kind="basic", headshot=False, power=False):
        self.kills += 1
        self.headshots += int(headshot)
        self.streak += 1
        self.multi_count += 1
        self.timer = self.COMBO_WINDOW
        self.multi_timer = self.MULTIKILL_WINDOW
        self.combo = min(4.0, 1.0 + (self.streak - 1) * 0.25)
        base = 100 + (150 if headshot else 0) + (500 if kind == "elite" else 0)
        base += 75 if power else 0
        if self.multi_count == 2:
            base += 250
        elif self.multi_count >= 3:
            base += 400
        self.last_award = round(base * self.combo)
        self.points += self.last_award
        return self.last_award

    def award_wave(self, round_number):
        value = 200 * round_number
        self.points += value
        return value

    def award_power(self):
        self.points += 25

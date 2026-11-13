"""Cooldown and duration state; visual effects live in the application."""
from dataclasses import dataclass


@dataclass
class Power:
    name: str
    recharge: float
    duration: float = 0.0
    cooldown: float = 0.0
    active: float = 0.0

    def activate(self):
        if self.cooldown > 0.0:
            return False
        self.cooldown = self.recharge
        self.active = self.duration
        return True

    def update(self, dt):
        self.cooldown = max(0.0, self.cooldown - dt)
        self.active = max(0.0, self.active - dt)


def make_powers():
    return {
        "dash": Power("dash", 4.0, 0.18),
        "pulse": Power("pulse", 10.0, 0.4),
        "vision": Power("vision", 18.0, 7.0),
        "fury": Power("fury", 24.0, 6.0),
    }

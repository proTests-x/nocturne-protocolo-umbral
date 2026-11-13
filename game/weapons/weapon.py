"""Weapon rules independent of Panda3D; spread is an angle in degrees."""
from dataclasses import dataclass


@dataclass(frozen=True)
class WeaponConfig:
    key: str
    name: str
    magazine: int
    reserve: int
    damage: float
    interval: float
    reload_time: float
    spread: float
    recoil: float
    pellets: int = 1
    automatic: bool = False
    range: float = 85.0


class Weapon:
    def __init__(self, config):
        self.config = config
        self.ammo = config.magazine
        self.reserve = config.reserve
        self.cooldown = 0.0
        self.reload_remaining = 0.0
        self.shots_fired = 0

    @property
    def reloading(self):
        return self.reload_remaining > 0

    @property
    def reload_progress(self):
        return 1 - self.reload_remaining / self.config.reload_time if self.reloading else 0

    def update(self, dt):
        self.cooldown = max(0, self.cooldown - dt)
        if self.reload_remaining > 0:
            self.reload_remaining = max(0, self.reload_remaining - dt)
            if self.reload_remaining == 0:
                transfer = min(self.config.magazine - self.ammo, self.reserve)
                self.ammo += transfer
                self.reserve -= transfer

    def fire(self, fury=False):
        if self.reloading or self.cooldown > 0 or self.ammo <= 0:
            return False
        self.ammo -= 1
        self.cooldown = self.config.interval / (1.35 if fury else 1)
        self.shots_fired += 1
        return True

    def reload(self):
        if self.reloading or self.ammo == self.config.magazine or self.reserve <= 0:
            return False
        self.reload_remaining = self.config.reload_time
        return True

    def cancel_reload(self):
        self.reload_remaining = 0

    def replenish(self):
        self.reserve = min(self.reserve + self.config.magazine * 2, self.config.reserve * 2)

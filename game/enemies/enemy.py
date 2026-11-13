"""Render-independent demon state and shared statistics."""
from dataclasses import dataclass


@dataclass(frozen=True)
class EnemyStats:
    hp: float
    speed: float
    damage: float
    radius: float
    height: float
    attack_interval: float


STATS = {
    "basic": EnemyStats(90, 2.7, 11, 0.43, 1.8, 1.15),
    "fast": EnemyStats(56, 4.5, 8, 0.34, 1.45, 0.85),
    "heavy": EnemyStats(285, 1.7, 25, 0.67, 2.55, 1.8),
    "ranged": EnemyStats(100, 2.2, 13, 0.42, 1.95, 2.3),
    "elite": EnemyStats(210, 3.65, 19, 0.49, 2.1, 1.3),
}


@dataclass
class Enemy:
    id: int
    kind: str
    x: float
    y: float
    z: float
    hp: float
    max_hp: float
    radius: float
    height: float
    speed: float
    damage: float
    attack_interval: float
    alive: bool = True
    heading: float = 0.0
    hit_flash: float = 0.0
    attack_timer: float = 0.8
    path_timer: float = 0.0
    path: list = None
    age: float = 0.0
    stagger: float = 0.0
    special_timer: float = 3.0
    charge_time: float = 0.0
    charge_dx: float = 0.0
    charge_dy: float = 0.0

    def __post_init__(self):
        if self.path is None:
            self.path = []


def make_enemy(identifier, kind, position, wave=1):
    """Infinite health/damage growth, bounded speed to preserve reaction time."""
    stats = STATS[kind]
    level = max(0, wave - 1)
    health = stats.hp * (1 + level * 0.115)
    return Enemy(
        identifier, kind, *position, health, health, stats.radius, stats.height,
        stats.speed * min(1.65, 1 + level * 0.022),
        stats.damage * (1 + level * 0.075), stats.attack_interval,
    )


@dataclass
class Projectile:
    id: int
    x: float
    y: float
    z: float
    vx: float
    vy: float
    vz: float
    damage: float
    radius: float = 0.18
    alive: bool = True
    lifetime: float = 5.0

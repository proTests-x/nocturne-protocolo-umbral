"""Weighted demon selection and staggered, distant portal spawns."""
from collections import deque
from math import cos, hypot, pi, sin

from game.enemies.enemy import STATS, make_enemy


class SpawnManager:
    MAX_ALIVE = 28

    def __init__(self, layout, rng):
        self.layout = layout
        self.rng = rng
        self.pending = deque()
        self.timer = 0.0
        self.round = 1
        self.next_id = 1

    def enqueue(self, round_number, count):
        self.round = round_number
        self.timer = 0.0
        special = min(0.64, 0.16 + 0.022 * round_number)
        kinds = ["basic", "fast", "heavy", "ranged", "elite"]
        weights = [1 - special, special * 0.32, special * 0.23,
                   special * 0.30, special * 0.15 if round_number >= 3 else 0]
        chosen = self.rng.choices(kinds, weights=weights, k=count)
        # Early rounds establish each threat without relying entirely on RNG.
        if round_number == 1:
            chosen = ["basic"] * max(0, count - 1) + ["fast"]
        elif round_number == 2 and count >= 2:
            chosen[-2:] = ["heavy", "ranged"]
        elif round_number == 3 and count:
            chosen[-1] = "elite"
        self.pending.extend(chosen)

    def update(self, dt, player_pos, alive_count):
        self.timer = max(0.0, self.timer - dt)
        if not self.pending or self.timer > 0.0 or alive_count >= self.MAX_ALIVE:
            return None
        points = list(self.layout.spawn_points)
        distant = [p for p in points if hypot(p[0] - player_pos[0], p[1] - player_pos[1]) >= 10]
        point = self.rng.choice(distant or points)
        kind = self.pending.popleft()
        # A portal marker can be close to cover. Resolve a nearby clear capsule
        # position so an enemy never starts embedded in the altar or masonry.
        if len(point) < 3 and not self.layout.walkable(point[0], point[1], STATS[kind].radius):
            candidates = [(point[0] + cos(i * pi / 4) * radius,
                           point[1] + sin(i * pi / 4) * radius)
                          for radius in (0.75, 1.5, 2.25) for i in range(8)]
            point = next((candidate for candidate in candidates
                          if self.layout.walkable(*candidate, STATS[kind].radius)), point)
        z = point[2] if len(point) >= 3 else self.layout.floor_height(point[0], point[1], ceiling=0.5)
        enemy = make_enemy(self.next_id, kind, (point[0], point[1], z), self.round)
        self.next_id += 1
        self.timer = max(0.23, 0.72 - self.round * 0.025)
        return enemy

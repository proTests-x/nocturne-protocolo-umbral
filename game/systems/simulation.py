"""Authoritative arena combat simulation, independent of Panda3D.

The renderer owns no damage rules. It drains ``events`` after each frame and
uses ``hit`` for weapon rays, keeping scoring and wave accounting consistent.
"""
import math
import random

from game.enemies.enemy import Projectile
from game.player.powers import make_powers
from .score_manager import ScoreManager
from .spawn_manager import SpawnManager
from .wave_manager import WaveManager


def _length(vector):
    return math.sqrt(sum(component * component for component in vector))


def _player_intersection(start, delta, player_pos, radius, player_height=1.65):
    """First normalized contact with the player's vertically bounded body.

    Intersect a swept sphere center with an expanded upright cylinder. This
    checks the whole segment, so fast projectiles cannot tunnel past players.
    """
    ox, oy = start[0] - player_pos[0], start[1] - player_pos[1]
    dx, dy, dz = delta
    reach = radius + 0.34
    a = dx * dx + dy * dy
    b = 2 * (ox * dx + oy * dy)
    c = ox * ox + oy * oy - reach * reach
    low, high = 0.0, 1.0
    if a < 1e-12:
        if c > 0:
            return None
    else:
        discriminant = b * b - 4 * a * c
        if discriminant < 0:
            return None
        root = math.sqrt(discriminant)
        low = max(low, (-b - root) / (2 * a))
        high = min(high, (-b + root) / (2 * a))
    bottom = player_pos[2] + 0.15 - radius
    top = player_pos[2] + player_height + radius
    if abs(dz) < 1e-12:
        if not bottom <= start[2] <= top:
            return None
    else:
        first, second = (bottom - start[2]) / dz, (top - start[2]) / dz
        low, high = max(low, min(first, second)), min(high, max(first, second))
    return low if low <= high else None


class Simulation:
    def __init__(self, layout, seed=7):
        self.layout = layout
        self.seed = seed
        self.reset()

    def reset(self):
        self.rng = random.Random(self.seed)
        self.enemies = []
        self.projectiles = []
        self.events = []
        self.score = ScoreManager()
        self.waves = WaveManager()
        self.spawns = SpawnManager(self.layout, self.rng)
        self.powers = make_powers()
        self.next_projectile = 1
        self.elapsed = 0.0
        self.player_height = 1.65

    def _visible(self, start, end):
        delta = tuple(b - a for a, b in zip(start, end))
        distance = _length(delta)
        if distance < 0.001:
            return True
        direction = tuple(value / distance for value in delta)
        hit = self.layout.raycast(start, direction, distance)
        return hit is None or hit >= distance - 0.1

    def hit(self, enemy, damage, headshot=False, power=False):
        if not enemy.alive or damage <= 0:
            return False
        enemy.hp = max(0.0, enemy.hp - damage)
        enemy.hit_flash = 0.13
        enemy.stagger = max(enemy.stagger, 0.08)
        if enemy.hp > 0:
            return False
        enemy.alive = False
        self.waves.on_kill()
        points = self.score.record_kill(enemy.kind, headshot, power)
        self.events.append({"type": "kill", "enemy": enemy, "headshot": headshot,
                            "points": points, "power": power})
        return True

    def use_power(self, name, player_pos, forward):
        power = self.powers.get(name)
        if power is None or not power.activate():
            return False
        self.score.award_power()
        self.events.append({"type": "power", "name": name, "position": player_pos})
        if name == "pulse":
            source = (player_pos[0], player_pos[1], player_pos[2] + 0.8)
            for enemy in self.enemies:
                if not enemy.alive:
                    continue
                dx, dy = enemy.x - player_pos[0], enemy.y - player_pos[1]
                distance = math.hypot(dx, dy)
                target = (enemy.x, enemy.y, enemy.z + enemy.height * 0.5)
                if distance > 8 or abs(enemy.z - player_pos[2]) > 3.0 or not self._visible(source, target):
                    continue
                self.hit(enemy, 130 * (1 - distance / 16), power=True)
                if enemy.alive:
                    enemy.stagger = 0.85
                    push = 2.8 * (1 - distance / 8)
                    if distance > 0.01:
                        # Short collision steps keep knockback out of thin walls.
                        steps = max(1, math.ceil(push / 0.2))
                        for _ in range(steps):
                            self._move(enemy, dx / distance * push / steps,
                                       dy / distance * push / steps, 0.02)
        return True

    def update(self, dt, player_pos, player_alive=True):
        if not player_alive or dt <= 0:
            return
        self.elapsed += dt
        self.score.update(dt)
        for power in self.powers.values():
            power.update(dt)
        self.enemies = [enemy for enemy in self.enemies if enemy.alive]
        self.projectiles = [shot for shot in self.projectiles if shot.alive]
        if self.waves.update(dt):
            self.spawns.enqueue(self.waves.round, self.waves.remaining)
            self.events.append({"type": "wave", "round": self.waves.round})
        spawned = self.spawns.update(dt, player_pos, len(self.enemies))
        if spawned:
            self.enemies.append(spawned)
            self.events.append({"type": "spawn", "enemy": spawned})
        # Movement clamps exceptional frame stalls; cooldowns still use real dt.
        motion_dt = min(dt, 0.1)
        for enemy in self.enemies:
            self._update_enemy(enemy, motion_dt, player_pos)
        for projectile in self.projectiles:
            self._update_projectile(projectile, dt, player_pos)
        if self.waves.active and self.waves.remaining == 0:
            self.waves.complete()
            points = self.score.award_wave(self.waves.round)
            self.events.append({"type": "wave_clear", "round": self.waves.round, "points": points})

    def _move(self, enemy, dx, dy, dt):
        # The heavy's wide capsule needs small steps: its radius leaves only
        # 8 cm of each stair tread before the following riser is contacted.
        limit = 0.065 if enemy.radius > 0.6 else 0.20
        steps = max(1, math.ceil(math.hypot(dx, dy) / limit))
        for _ in range(steps):
            enemy.x, enemy.y = self.layout.move(enemy.x, enemy.y, enemy.z, dx / steps, dy / steps,
                                                radius=enemy.radius, step_height=0.4)
            floor = self.layout.floor_height(enemy.x, enemy.y, ceiling=enemy.z + 0.42)
            enemy.z = max(floor, enemy.z - 9.8 * dt / steps)

    def _damage_player(self, amount):
        # A short invulnerable dash rewards timing without extending its duration.
        if self.powers["dash"].active <= 0:
            self.events.append({"type": "damage", "amount": amount})

    def _stair_route(self, enemy, player_pos):
        """Bridge the ground A* graph to an elevated gallery via its stairs.

        Geometry tags keep this independent of a particular left/right gallery
        coordinate. Once on a staircase, only the remaining risers are routed.
        """
        blocks = getattr(self.layout, "blocks", ())
        platforms = [block for block in blocks if block.name == "platform"
                     and block.contains(player_pos[0], player_pos[1])
                     and block.top <= player_pos[2] + 0.45
                     and enemy.z < block.top - 0.15]
        if not platforms:
            return None
        platform = max(platforms, key=lambda block: block.top)
        steps = sorted((block for block in blocks if block.name == "step"
                        and abs(block.x - platform.x) < 0.1), key=lambda block: block.top)
        if not steps:
            return None
        first, last = steps[0], steps[-1]
        approach = (first.x, first.y - first.d * 0.5 - 0.65)
        on_stairs = (abs(enemy.x - first.x) < first.w * 0.5 - enemy.radius
                     and first.y - first.d * 0.5 - 0.5 <= enemy.y <= last.y + last.d)
        if on_stairs:
            route = [(step.x, step.y) for step in steps if step.y > enemy.y + 0.15]
        else:
            route = list(self.layout.path((enemy.x, enemy.y), approach))
            route.append(approach)
            route.extend((step.x, step.y) for step in steps)
        route.extend(((last.x, last.y + last.d * 1.2), (player_pos[0], player_pos[1])))
        return route

    def _update_enemy(self, enemy, dt, player_pos):
        enemy.age += dt
        enemy.hit_flash = max(0.0, enemy.hit_flash - dt)
        enemy.attack_timer = max(0.0, enemy.attack_timer - dt)
        enemy.path_timer -= dt
        enemy.special_timer -= dt
        enemy.stagger = max(0.0, enemy.stagger - dt)
        if enemy.stagger > 0:
            return
        dx, dy = player_pos[0] - enemy.x, player_pos[1] - enemy.y
        distance = math.hypot(dx, dy)
        if distance < 0.001:
            dx, dy, distance = 0.0, 0.001, 0.001
        ux, uy = dx / distance, dy / distance
        enemy.heading = math.degrees(math.atan2(-ux, uy))
        chest = (enemy.x, enemy.y, enemy.z + enemy.height * 0.65)
        target = (player_pos[0], player_pos[1], player_pos[2] + self.player_height * 0.58)
        visible = self._visible(chest, target)
        # Seeing over low cover is sufficient to attack, but not to walk through
        # it. Navigation casts near the feet and along both capsule edges.
        path_clear = visible
        if path_clear:
            low_source = (enemy.x, enemy.y, enemy.z + 0.44)
            low_target = (player_pos[0], player_pos[1], player_pos[2] + 0.44)
            for side in (-1, 0, 1):
                offset = (-uy * enemy.radius * side, ux * enemy.radius * side, 0)
                if not self._visible(tuple(a + b for a, b in zip(low_source, offset)),
                                     tuple(a + b for a, b in zip(low_target, offset))):
                    path_clear = False
                    break
        stair_route = self._stair_route(enemy, player_pos) if enemy.path_timer <= 0 else None
        needs_stairs = player_pos[2] > enemy.z + 0.5
        if needs_stairs:
            path_clear = False
        melee_reach = enemy.radius + 0.9
        vertical_contact = (player_pos[2] < enemy.z + enemy.height + 0.15
                            and player_pos[2] + self.player_height > enemy.z)

        if distance < melee_reach and visible and vertical_contact and enemy.attack_timer <= 0:
            self._damage_player(enemy.damage)
            enemy.attack_timer = enemy.attack_interval
            return
        if enemy.kind == "ranged" and visible and 3 < distance < 21 and enemy.attack_timer <= 0:
            self._fire_projectile(enemy, chest, target)
            enemy.attack_timer = enemy.attack_interval

        travel_x, travel_y = ux, uy
        if not path_clear:
            if enemy.path_timer <= 0:
                enemy.path = stair_route if stair_route is not None else list(
                    self.layout.path((enemy.x, enemy.y), (player_pos[0], player_pos[1])))
                enemy.path_timer = 0.9 + (enemy.id % 5) * 0.08
            while enemy.path and math.hypot(enemy.path[0][0] - enemy.x, enemy.path[0][1] - enemy.y) < 0.7:
                enemy.path.pop(0)
            if enemy.path:
                px, py = enemy.path[0][0] - enemy.x, enemy.path[0][1] - enemy.y
                size = max(0.001, math.hypot(px, py))
                travel_x, travel_y = px / size, py / size
        else:
            enemy.path.clear()
            if enemy.kind == "ranged" and distance < 12:
                travel_x, travel_y = (-ux, -uy) if distance < 8 else (-uy * 0.5, ux * 0.5)
            elif distance < melee_reach * 0.9:
                travel_x = travel_y = 0.0

        speed = enemy.speed
        if enemy.kind == "elite" and visible:
            if enemy.special_timer <= 0 and 3 < distance < 14:
                enemy.charge_time = 0.55
                enemy.charge_dx, enemy.charge_dy = ux, uy
                enemy.special_timer = 5.0
            if enemy.charge_time > 0:
                enemy.charge_time = max(0.0, enemy.charge_time - dt)
                travel_x, travel_y = enemy.charge_dx, enemy.charge_dy
                speed *= 2.8
            elif distance > 3:
                strafe = math.sin(enemy.age * 2.3 + enemy.id) * 0.55
                travel_x -= uy * strafe
                travel_y += ux * strafe

        # Gentle local separation avoids visually intersecting demon crowds.
        separate_x = separate_y = 0.0
        for other in self.enemies:
            if other is enemy or not other.alive or abs(other.z - enemy.z) > 1:
                continue
            sx, sy = enemy.x - other.x, enemy.y - other.y
            separation = math.hypot(sx, sy)
            desired = enemy.radius + other.radius + 0.08
            if separation <= 0.001:
                angle = enemy.id * 2.399963
                separate_x += math.cos(angle)
                separate_y += math.sin(angle)
                continue
            if 0.001 < separation < desired:
                strength = (desired - separation) / desired
                separate_x += sx / separation * strength
                separate_y += sy / separation * strength
        mx = (travel_x * speed + separate_x * 2.0) * dt
        my = (travel_y * speed + separate_y * 2.0) * dt
        steps = max(1, math.ceil(math.hypot(mx, my) / 0.22))
        for _ in range(steps):
            self._move(enemy, mx / steps, my / steps, dt / steps)

    def _fire_projectile(self, enemy, source, target):
        delta = tuple(b - a for a, b in zip(source, target))
        distance = max(0.01, _length(delta))
        speed = 10.0 + min(5.0, self.waves.round * 0.18)
        velocity = tuple(component / distance * speed for component in delta)
        projectile = Projectile(self.next_projectile, *source, *velocity, enemy.damage)
        self.next_projectile += 1
        self.projectiles.append(projectile)
        self.events.append({"type": "projectile", "projectile": projectile})

    def _update_projectile(self, projectile, dt, player_pos):
        start = (projectile.x, projectile.y, projectile.z)
        # A frame longer than remaining lifetime must not extend its range.
        travel_dt = min(dt, projectile.lifetime)
        delta = (projectile.vx * travel_dt, projectile.vy * travel_dt, projectile.vz * travel_dt)
        distance = _length(delta)
        wall_t = None
        if distance > 0.00001:
            direction = tuple(component / distance for component in delta)
            r = projectile.radius
            offsets = ((0, 0, 0), (r, 0, 0), (-r, 0, 0), (0, r, 0),
                       (0, -r, 0), (0, 0, r), (0, 0, -r))
            # Offset sweeps conservatively cover the orb radius near cover edges.
            for offset in offsets:
                origin = tuple(a + b for a, b in zip(start, offset))
                wall_distance = self.layout.raycast(origin, direction, distance)
                if wall_distance is not None:
                    fraction = max(0.0, wall_distance / distance)
                    wall_t = fraction if wall_t is None else min(wall_t, fraction)
        player_t = _player_intersection(start, delta, player_pos, projectile.radius, self.player_height)
        if player_t is not None and (wall_t is None or player_t < wall_t):
            self._damage_player(projectile.damage)
            projectile.alive = False
        elif wall_t is not None:
            projectile.alive = False
        fraction = min(1.0, wall_t if wall_t is not None else 1.0,
                       player_t if player_t is not None else 1.0)
        projectile.x += delta[0] * fraction
        projectile.y += delta[1] * fraction
        projectile.z += delta[2] * fraction
        projectile.lifetime -= dt
        if projectile.lifetime <= 0:
            projectile.alive = False

"""Engine-independent, substepped FPS motion with sliding collision."""
import math
from game import config


def approach(value, target, rate, dt):
    return value + (target - value) * (1.0 - math.exp(-rate * dt))


class Movement:
    def __init__(self, layout):
        self.layout = layout
        self.reset()

    def reset(self):
        self.x, self.y, self.z = 0.0, -17.0, 0.0
        self.vx = self.vy = self.vz = 0.0
        self.grounded = True
        self.sprinting = self.crouching = False
        self.slide_remaining = self.dash_remaining = 0.0
        self.slide_direction = (0.0, 1.0)
        self.dash_direction = (0.0, 1.0)
        self.eye_height = config.STANDING_HEIGHT
        self.bob_phase = self.landing = 0.0
        self._last_crouch = False

    @property
    def pos(self):
        return self.x, self.y, self.z

    @property
    def speed(self):
        return math.hypot(self.vx, self.vy)

    def jump(self):
        if self.grounded:
            self.vz = config.JUMP_SPEED
            self.grounded = False
            self.slide_remaining = 0

    def dash(self, forward):
        self.dash_direction = forward
        self.dash_remaining = 0.19

    def update(self, dt, keys, yaw, ads=False, fury=False):
        # Small collision steps prevent sprint/dash tunnelling during slow frames.
        steps = max(1, math.ceil(dt / (1 / 100)))
        for _ in range(steps):
            self._step(dt / steps, keys, yaw, ads, fury)

    def _step(self, dt, keys, yaw, ads, fury):
        heading = math.radians(yaw)
        forward = (-math.sin(heading), math.cos(heading))
        right = (math.cos(heading), math.sin(heading))
        forward_input = float(keys.get('w', False)) - float(keys.get('s', False))
        side_input = float(keys.get('d', False)) - float(keys.get('a', False))
        length = max(1.0, math.hypot(forward_input, side_input))
        dx = (forward[0] * forward_input + right[0] * side_input) / length
        dy = (forward[1] * forward_input + right[1] * side_input) / length
        crouch = bool(keys.get('control', False) or keys.get('c', False))
        if crouch and not self._last_crouch and self.sprinting and self.grounded and self.speed > 5:
            self.slide_remaining = 0.82
            self.slide_direction = (self.vx / self.speed, self.vy / self.speed)
        self._last_crouch = crouch
        self.crouching = crouch or self.slide_remaining > 0
        self.sprinting = bool(keys.get('shift', False) and forward_input > 0 and not ads and not self.crouching)
        speed = config.CROUCH_SPEED if self.crouching else config.SPRINT_SPEED if self.sprinting else config.WALK_SPEED
        speed *= 1.24 if fury else 1.0
        speed *= 0.65 if ads else 1.0
        self.vx = approach(self.vx, dx * speed, 12 if self.grounded else 3.5, dt)
        self.vy = approach(self.vy, dy * speed, 12 if self.grounded else 3.5, dt)
        if self.slide_remaining > 0:
            self.slide_remaining = max(0, self.slide_remaining - dt)
            speed = 5 + 7 * self.slide_remaining / 0.82
            self.vx, self.vy = (c * speed for c in self.slide_direction)
        if self.dash_remaining > 0:
            self.dash_remaining = max(0, self.dash_remaining - dt)
            self.vx, self.vy = (c * 32 for c in self.dash_direction)
        self.x, self.y = self.layout.move(self.x, self.y, self.z, self.vx * dt, self.vy * dt,
                                           radius=config.PLAYER_RADIUS, step_height=0.38 if self.grounded else 0)
        previous_z = self.z
        floor = self.layout.floor_height(self.x, self.y, ceiling=previous_z + (0.39 if self.grounded else 0.02))
        self.vz -= config.GRAVITY * dt
        self.z += self.vz * dt
        if self.z <= floor and self.vz <= 0:
            if not self.grounded:
                self.landing = min(0.13, abs(self.vz) * 0.009)
            self.z, self.vz, self.grounded = floor, 0.0, True
        else:
            self.grounded = False
        target_height = config.CROUCH_HEIGHT if self.crouching else config.STANDING_HEIGHT
        self.eye_height = approach(self.eye_height, target_height, 13, dt)
        self.landing = approach(self.landing, 0, 12, dt)
        self.bob_phase += self.speed * dt * (1.9 if self.sprinting else 1.6)

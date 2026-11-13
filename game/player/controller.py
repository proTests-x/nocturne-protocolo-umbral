"""Smooth FPS camera. Mouse capture is enabled only during live play."""
import math
from panda3d.core import WindowProperties
from game import config
from .movement import Movement, approach


class PlayerController:
    def __init__(self, base, layout):
        self.base = base
        self.movement = Movement(layout)
        self.keys = {}
        self.reset()

    def reset(self):
        self.movement.reset()
        self.keys.clear()
        self.yaw = self.pitch = self.recoil = 0.0
        self.ads = self.shake = 0.0
        self.fov = config.FOV
        self.captured = False
        self.ignore_mouse_frames = 3

    def capture(self, enabled):
        self.captured = enabled
        self.keys.clear()
        self.ignore_mouse_frames = 3
        if not hasattr(self.base.win, 'requestProperties'):
            return
        props = WindowProperties()
        props.setCursorHidden(enabled)
        # Confined mode plus recenter works on Windows, including the 1.10 driver.
        props.setMouseMode(WindowProperties.M_confined if enabled else WindowProperties.M_absolute)
        self.base.win.requestProperties(props)
        if enabled:
            self.base.win.movePointer(0, self.base.win.getXSize() // 2, self.base.win.getYSize() // 2)

    @property
    def forward(self):
        heading = math.radians(self.yaw)
        return -math.sin(heading), math.cos(heading)

    def read_mouse(self):
        if not self.captured or not hasattr(self.base.win, 'getPointer'):
            return
        pointer = self.base.win.getPointer(0)
        cx, cy = self.base.win.getXSize() // 2, self.base.win.getYSize() // 2
        dx, dy = pointer.getX() - cx, pointer.getY() - cy
        if self.ignore_mouse_frames:
            self.ignore_mouse_frames -= 1
        else:
            sensitivity = config.MOUSE_SENSITIVITY * (1 - self.ads * 0.43)
            self.yaw -= max(-250, min(250, dx)) * sensitivity
            self.pitch = max(-84, min(84, self.pitch - max(-200, min(200, dy)) * sensitivity))
        self.base.win.movePointer(0, cx, cy)

    def update(self, dt, aiming, fury=False, mouse=True):
        if mouse:
            self.read_mouse()
        self.ads = approach(self.ads, 1 if aiming else 0, 13, dt)
        self.movement.update(dt, self.keys, self.yaw, self.ads > 0.5, fury)
        self.recoil = approach(self.recoil, 0, 10, dt)
        self.shake = approach(self.shake, 0, 9, dt)
        movement = self.movement
        weight = min(1, movement.speed / 5) if movement.grounded else 0
        bob = math.sin(movement.bob_phase * 2) * 0.026 * weight * (1 - self.ads * 0.8)
        tilt = math.sin(movement.bob_phase) * 0.28 * weight
        tilt += -movement.slide_direction[0] * 2.8 if movement.slide_remaining else 0
        target_fov = config.ADS_FOV if aiming else config.SPRINT_FOV if movement.sprinting or movement.dash_remaining else config.FOV
        self.fov = approach(self.fov, target_fov, 8, dt)
        self.base.camLens.setFov(self.fov)
        self.base.camera.setPos(movement.x, movement.y, movement.z + movement.eye_height + bob - movement.landing)
        shake = math.sin(self.base.elapsed * 73) * self.shake
        self.base.camera.setHpr(self.yaw + shake, self.pitch + self.recoil + shake * 0.7, tilt + shake)

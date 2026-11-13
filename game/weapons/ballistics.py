"""Analytic hit tests: world occlusion is resolved before enemy hitboxes."""
import math


def ray_box(origin, direction, low, high, limit):
    near, far = 0.0, limit
    for axis in range(3):
        if abs(direction[axis]) < 1e-8:
            if origin[axis] < low[axis] or origin[axis] > high[axis]:
                return None
        else:
            a = (low[axis] - origin[axis]) / direction[axis]
            b = (high[axis] - origin[axis]) / direction[axis]
            near, far = max(near, min(a, b)), min(far, max(a, b))
            if near > far:
                return None
    return near if near <= limit else None


def trace(layout, enemies, origin, direction, distance=85):
    """Return (enemy or None, headshot, distance), respecting solid cover."""
    magnitude = math.sqrt(sum(v*v for v in direction))
    if magnitude < 1e-9:
        return None, False, 0.0
    direction = tuple(v / magnitude for v in direction)
    wall = layout.raycast(origin, direction, distance)
    nearest = wall if wall is not None else distance
    target, headshot = None, False
    for enemy in enemies:
        if not enemy.alive:
            continue
        r, h = enemy.radius, enemy.height
        # Separate head and trunk volumes make headshots possible above cover.
        for is_head, width, bottom, top in ((False, r, .10*h, .76*h), (True, r*.60, .76*h, h)):
            hit = ray_box(origin, direction, (enemy.x-width, enemy.y-width, enemy.z+bottom),
                          (enemy.x+width, enemy.y+width, enemy.z+top), nearest)
            if hit is not None and hit < nearest:
                target, headshot, nearest = enemy, is_head, hit
    return target, headshot, nearest

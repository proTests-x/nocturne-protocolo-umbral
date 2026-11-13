"""The arena's single source of truth for collision and navigation.

This module intentionally has no Panda3D dependency. Coordinates use Z up,
Y north. Boxes have a centred XY footprint and a bottom Z, in metres.
"""

from dataclasses import dataclass
import heapq
import math


@dataclass(frozen=True)
class AABB:
    x: float
    y: float
    z: float
    w: float
    d: float
    h: float
    name: str = "stone"

    @property
    def top(self):
        return self.z + self.h

    def contains(self, x, y, padding=0.0):
        return (abs(x - self.x) < self.w * .5 + padding
                and abs(y - self.y) < self.d * .5 + padding)


class ArenaLayout:
    """Compact courtyard, stepped galleries and an accessible chapel."""

    bounds = 26.0

    def __init__(self):
        self.blocks = []
        self._build()
        self.spawn_points = [
            (-21, -21), (21, -21), (-21, 20), (21, 20),
            (-23, 4), (23, 4), (-7, 22), (7, 22), (0, 22),
            (-21, -10), (21, -10), (-7, -22), (7, -22),
        ]
        self._grid_step = 1.0
        self._walk_cells = None

    def _add(self, x, y, z, w, d, h, name="stone"):
        self.blocks.append(AABB(x, y, z, w, d, h, name))

    def _build(self):
        # Boundary walls also stop bullets. Their outer faces enclose 52 m.
        self._add(-26.5, 0, 0, 1, 54, 5.2, "boundary")
        self._add(26.5, 0, 0, 1, 54, 5.2, "boundary")
        self._add(0, -26.5, 0, 52, 1, 5.2, "boundary")
        self._add(0, 26.5, 0, 52, 1, 5.2, "boundary")

        # A chapel you can actually enter through its six metre doorway.
        self._add(-10.4, 20.5, 0, .8, 11, 7.8, "chapel_wall")
        self._add(10.4, 20.5, 0, .8, 11, 7.8, "chapel_wall")
        self._add(0, 25.5, 0, 20, 1, 7.8, "chapel_wall")
        self._add(-6.6, 15.4, 0, 7.6, .8, 7.8, "chapel_front")
        self._add(6.6, 15.4, 0, 7.6, .8, 7.8, "chapel_front")
        self._add(0, 15.4, 5.7, 5.6, .8, 2.1, "chapel_lintel")
        self._add(0, 20.6, 7.8, 21.6, 11.8, .55, "chapel_roof")
        self._add(0, 23.8, 0, 4, 1.2, 1.1, "altar")

        # Twin galleries. Nested steps have 0.3 m risers and generous treads.
        for side in (-1, 1):
            x = side * 15.7
            self._add(x, 0.5, 0, 6.4, 8.0, 1.8, "platform")
            for step in range(6):
                self._add(x, -7.625 + step * .75, 0, 3.6, .75,
                          .3 * (step + 1), "step")
            self._add(x + side * 3.0, .5, 1.8, .4, 8, 1.05, "parapet")
            self._add(x, 4.3, 1.8, 6.4, .4, 1.05, "parapet")

        # Cover on both approaches, deliberately leaving the centre open.
        for x, y, w, d, h in [
            (-6.5, -7.0, 3.8, 1.3, 1.15), (6.5, -7.0, 3.8, 1.3, 1.15),
            (-7.2, 6.8, 1.5, 3.5, 1.45), (7.2, 6.8, 1.5, 3.5, 1.45),
            (-18.5, 13.0, 3.2, 2.2, 1.4), (18.5, 13.0, 3.2, 2.2, 1.4),
            (-16.5, -18.0, 4.8, 1.4, 1.25), (16.5, -18.0, 4.8, 1.4, 1.25),
        ]:
            self._add(x, y, 0, w, d, h, "cover")

        # Buttresses give side corridors and strong silhouettes.
        for side in (-1, 1):
            for y in (-22, -13, -3, 7, 18):
                self._add(side * 24.9, y, 0, 2.2, 1.4, 7.6, "buttress")

    def floor_height(self, x, y, ceiling=999):
        """Highest surface beneath *ceiling*, or the courtyard at zero."""
        height = 0.0
        for block in self.blocks:
            if block.top <= ceiling + 1e-6 and block.contains(x, y):
                height = max(height, block.top)
        return height

    @staticmethod
    def _touches(block, x, y, radius):
        # Circle-vs-rectangle avoids snagging at rectangular corner padding.
        near_x = max(block.x - block.w / 2, min(x, block.x + block.w / 2))
        near_y = max(block.y - block.d / 2, min(y, block.y + block.d / 2))
        return (near_x - x) ** 2 + (near_y - y) ** 2 < radius * radius - 1e-8

    def _blocked(self, x, y, z, radius, step_height):
        if abs(x) > self.bounds - radius or abs(y) > self.bounds - radius:
            return True
        for block in self.blocks:
            # z is feet height; keep clearance for a standing actor.
            if block.top <= z + step_height + 1e-5 or block.z >= z + 1.75:
                continue
            if self._touches(block, x, y, radius):
                return True
        return False

    def move(self, x, y, z, dx, dy, radius=.35, step_height=.38):
        """Move a capsule horizontally, with stepping and wall sliding.

        Substeps prevent a dash or a slow frame from tunnelling through thin
        walls. Vertical velocity / gravity belong to the player controller.
        """
        distance = math.hypot(dx, dy)
        count = max(1, math.ceil(distance / max(.12, radius * .7)))
        sx, sy = dx / count, dy / count
        current_z = z
        for _ in range(count):
            if not self._blocked(x + sx, y + sy, current_z, radius, step_height):
                x, y = x + sx, y + sy
            else:
                if not self._blocked(x + sx, y, current_z, radius, step_height):
                    x += sx
                if not self._blocked(x, y + sy, current_z, radius, step_height):
                    y += sy
            # A long move may climb several stairs, one riser at a time.
            current_z = max(current_z, self.floor_height(x, y, current_z + step_height))
        return x, y

    def raycast(self, origin, direction, max_distance=100):
        """Return nearest world hit distance for a (possibly non-unit) ray."""
        length = math.sqrt(sum(v * v for v in direction))
        if length < 1e-10 or max_distance <= 0:
            return None
        direction = tuple(v / length for v in direction)
        closest = float(max_distance)
        found = False
        if direction[2] < -1e-10:
            t = -origin[2] / direction[2]
            if 0 <= t <= closest:
                closest, found = t, True
        for block in self.blocks:
            mins = (block.x - block.w / 2, block.y - block.d / 2, block.z)
            maxs = (block.x + block.w / 2, block.y + block.d / 2, block.top)
            enter, leave = 0.0, closest
            valid = True
            for axis in range(3):
                if abs(direction[axis]) < 1e-10:
                    if not mins[axis] <= origin[axis] <= maxs[axis]:
                        valid = False
                        break
                else:
                    t1 = (mins[axis] - origin[axis]) / direction[axis]
                    t2 = (maxs[axis] - origin[axis]) / direction[axis]
                    enter = max(enter, min(t1, t2))
                    leave = min(leave, max(t1, t2))
                    if enter > leave:
                        valid = False
                        break
            if valid and 0 <= enter <= closest:
                closest, found = enter, True
        return closest if found else None

    def walkable(self, x, y, radius=.55):
        """Whether a ground-level AI capsule has enough clearance here."""
        return not self._blocked(x, y, 0, radius, .38)

    def _grid(self):
        if self._walk_cells is None:
            edge = int(self.bounds) - 1
            self._walk_cells = {
                (x, y) for x in range(-edge, edge + 1)
                for y in range(-edge, edge + 1) if self.walkable(x, y)
            }
        return self._walk_cells

    def _nearest_cell(self, point, cells):
        rounded = (round(point[0]), round(point[1]))
        if rounded in cells:
            return rounded
        return min(cells, key=lambda cell: (cell[0] - point[0]) ** 2
                   + (cell[1] - point[1]) ** 2)

    def path(self, start, end):
        """A* path around cover; targets above ground snap to nearest aisle.

        Returned waypoints omit the starting cell. Diagonal corner cutting is
        forbidden so large demons do not plan routes through masonry.
        """
        cells = self._grid()
        first, last = self._nearest_cell(start, cells), self._nearest_cell(end, cells)
        if first == last:
            return [(float(last[0]), float(last[1]))]
        frontier = [(0.0, first)]
        cost = {first: 0.0}
        previous = {}
        offsets = [(-1, 0), (1, 0), (0, -1), (0, 1),
                   (-1, -1), (-1, 1), (1, -1), (1, 1)]
        while frontier:
            _, here = heapq.heappop(frontier)
            if here == last:
                route = []
                while here != first:
                    route.append((float(here[0]), float(here[1])))
                    here = previous[here]
                return list(reversed(route))
            for dx, dy in offsets:
                there = (here[0] + dx, here[1] + dy)
                if there not in cells:
                    continue
                if dx and dy and ((here[0] + dx, here[1]) not in cells
                                  or (here[0], here[1] + dy) not in cells):
                    continue
                new_cost = cost[here] + (1.41421356 if dx and dy else 1.0)
                if new_cost >= cost.get(there, float("inf")):
                    continue
                cost[there], previous[there] = new_cost, here
                heuristic = math.hypot(last[0] - there[0], last[1] - there[1])
                heapq.heappush(frontier, (new_cost + heuristic, there))
        return []

"""World collision regressions can run without graphics or Panda3D."""

import math
import unittest
from game.world.layout import ArenaLayout


class ArenaLayoutTests(unittest.TestCase):
    def setUp(self):
        self.layout = ArenaLayout()

    def test_all_spawns_are_reachable_from_courtyard(self):
        for spawn in self.layout.spawn_points:
            with self.subTest(spawn=spawn):
                self.assertTrue(self.layout.walkable(*spawn))
                route = self.layout.path((0, 0), spawn)
                self.assertTrue(route)
                self.assertLess(math.dist(route[-1], spawn), 1)

    def test_dash_does_not_tunnel_through_cover_or_boundary(self):
        x, y = self.layout.move(-6.5, -13, 0, 0, 15)
        self.assertLess(y, -7.9)
        self.assertAlmostEqual(x, -6.5)
        x, _ = self.layout.move(0, -11, 0, 100, 0)
        self.assertLessEqual(x, 25.65)

    def test_obstacle_allows_sideways_sliding(self):
        x, y = self.layout.move(-6.5, -8.2, 0, 2, 2)
        self.assertGreater(x, -5)
        self.assertLess(y, -7.9)

    def test_chapel_opening_is_passable_and_roof_is_not_floor(self):
        x, y = self.layout.move(0, 13, 0, 0, 7)
        self.assertAlmostEqual(y, 20)
        self.assertAlmostEqual(x, 0)
        self.assertEqual(self.layout.floor_height(0, 20, .38), 0)
        self.assertGreater(self.layout.floor_height(0, 20), 7)

    def test_stairs_are_traversable_and_have_consistent_risers(self):
        x, y, z = 15.7, -8.5, 0
        for _ in range(95):
            x, y = self.layout.move(x, y, z, 0, .075)
            z = self.layout.floor_height(x, y, z + .38)
        self.assertGreater(y, -2)
        self.assertAlmostEqual(z, 1.8)
        self.assertEqual(self.layout.floor_height(15.7, -7.5, .38), .3)

    def test_ray_hits_closest_cover_and_ground(self):
        distance = self.layout.raycast((-6.5, -13, .7), (0, 1, 0))
        self.assertAlmostEqual(distance, 5.35)
        self.assertAlmostEqual(self.layout.raycast((0, 0, 2), (0, 0, -2)), 2)
        self.assertIsNone(self.layout.raycast((0, 0, 2), (0, 0, 1), 3))

    def test_path_routes_around_cover_and_forbids_corner_cutting(self):
        route = self.layout.path((-6.5, -10), (-6.5, -4))
        self.assertTrue(route)
        self.assertTrue(all(self.layout.walkable(*point) for point in route))
        self.assertTrue(any(abs(point[0] + 6.5) > 2 for point in route))


if __name__ == "__main__":
    unittest.main()

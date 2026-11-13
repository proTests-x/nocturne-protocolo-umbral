"""Pure ray-hit regressions; these tests never initialize the renderer."""
import unittest

from game.enemies.enemy import make_enemy
from game.weapons.ballistics import ray_box, trace
from game.world.layout import AABB, ArenaLayout


class OpenArena(ArenaLayout):
    def _build(self):
        pass


class BallisticsTests(unittest.TestCase):
    def setUp(self):
        self.layout = OpenArena()
        self.near = make_enemy(1, "basic", (0, 4, 0))
        self.far = make_enemy(2, "basic", (0, 8, 0))

    def test_front_wall_occludes_enemy(self):
        self.layout.blocks.append(AABB(0, 2, 0, 4, 0.2, 3))
        enemy, headshot, distance = trace(self.layout, [self.near], (0, 0, 1), (0, 1, 0))
        self.assertIsNone(enemy)
        self.assertFalse(headshot)
        self.assertAlmostEqual(distance, 1.9)

    def test_nearest_target_wins_regardless_of_list_order(self):
        for enemies in ([self.near, self.far], [self.far, self.near]):
            enemy, headshot, distance = trace(self.layout, enemies, (0, 0, 1), (0, 1, 0))
            self.assertIs(enemy, self.near)
            self.assertFalse(headshot)
            self.assertAlmostEqual(distance, 4 - self.near.radius)

    def test_headshot_and_body_hit_are_distinct(self):
        body = trace(self.layout, [self.near], (0, 0, 1), (0, 1, 0))
        head = trace(self.layout, [self.near], (0, 0, 1.62), (0, 1, 0))
        self.assertIs(body[0], self.near)
        self.assertFalse(body[1])
        self.assertIs(head[0], self.near)
        self.assertTrue(head[1])

    def test_head_is_exposed_above_low_cover(self):
        self.layout.blocks.append(AABB(0, 2, 0, 4, 0.2, 1.2))
        self.assertIsNone(trace(self.layout, [self.near], (0, 0, 1), (0, 1, 0))[0])
        enemy, headshot, _ = trace(self.layout, [self.near], (0, 0, 1.62), (0, 1, 0))
        self.assertIs(enemy, self.near)
        self.assertTrue(headshot)

    def test_elevated_enemy_hitbox_follows_its_feet(self):
        self.near.z = 1.8
        self.assertIsNone(trace(self.layout, [self.near], (0, 0, 1), (0, 1, 0))[0])
        enemy, headshot, _ = trace(self.layout, [self.near], (0, 0, 3.42), (0, 1, 0))
        self.assertIs(enemy, self.near)
        self.assertTrue(headshot)

    def test_dead_enemies_do_not_shield_living_enemies(self):
        self.near.alive = False
        enemy, _, _ = trace(self.layout, [self.near, self.far], (0, 0, 1), (0, 1, 0))
        self.assertIs(enemy, self.far)

    def test_direction_normalization_and_range_limit(self):
        unit = trace(self.layout, [self.near], (0, 0, 1), (0, 1, 0))
        scaled = trace(self.layout, [self.near], (0, 0, 1), (0, 9, 0))
        self.assertEqual(unit, scaled)
        self.assertEqual(trace(self.layout, [self.near], (0, 0, 1), (0, 1, 0), 2),
                         (None, False, 2))
        self.assertEqual(trace(self.layout, [self.near], (0, 0, 1), (0, 0, 0)),
                         (None, False, 0))

    def test_parallel_ray_outside_box_misses(self):
        self.assertIsNone(ray_box((2, 0, 1), (0, 1, 0), (-1, 3, 0), (1, 5, 2), 20))
        self.assertIsNone(ray_box((0, 0, 1), (0, -1, 0), (-1, 3, 0), (1, 5, 2), 20))


if __name__ == "__main__":
    unittest.main()

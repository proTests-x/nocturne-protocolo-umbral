"""Combat regression tests: run with python -m unittest discover -s tests."""
import math
import random
import unittest

from game.enemies.enemy import Projectile, make_enemy
from game.player.powers import make_powers
from game.systems.score_manager import ScoreManager
from game.systems.simulation import Simulation
from game.systems.spawn_manager import SpawnManager
from game.systems.wave_manager import WaveManager
from game.world.layout import AABB, ArenaLayout


class EmptyArena(ArenaLayout):
    def _build(self):
        pass


class CombatTests(unittest.TestCase):
    def setUp(self):
        self.layout = EmptyArena()
        self.sim = Simulation(self.layout)
        # Prevent wave transitions in isolated combat cases.
        self.sim.waves.intermission = 1000

    def add_enemy(self, kind="basic", position=(0, 3, 0)):
        enemy = make_enemy(len(self.sim.enemies) + 1, kind, position)
        self.sim.enemies.append(enemy)
        self.sim.waves.remaining += 1
        return enemy

    def damage_events(self):
        return [event for event in self.sim.events if event["type"] == "damage"]

    def test_death_is_counted_once(self):
        enemy = self.add_enemy()
        self.assertTrue(self.sim.hit(enemy, 1000, headshot=True))
        self.assertFalse(self.sim.hit(enemy, 1000, headshot=True))
        self.assertEqual(self.sim.score.points, 250)
        self.assertEqual(self.sim.score.kills, 1)
        self.assertEqual(self.sim.waves.remaining, 0)

    def test_combo_multikill_and_expiry(self):
        score = ScoreManager()
        self.assertEqual(score.record_kill(), 100)
        self.assertEqual(score.record_kill(), round(350 * 1.25))
        self.assertEqual(score.record_kill(), 750)
        self.assertEqual(score.combo, 1.5)
        score.update(4)
        self.assertEqual(score.combo, 1)
        self.assertEqual(score.streak, 0)
        self.assertEqual(score.record_kill("elite"), 600)

    def test_power_cooldown_and_duration_are_independent(self):
        power = make_powers()["vision"]
        self.assertTrue(power.activate())
        self.assertFalse(power.activate())
        power.update(7)
        self.assertEqual(power.active, 0)
        self.assertEqual(power.cooldown, 11)
        power.update(11)
        self.assertTrue(power.activate())

    def test_pulse_kills_nearby_and_respects_cover(self):
        near = self.add_enemy(position=(0, 2, 0))
        blocked = self.add_enemy(position=(3, 0, 0))
        self.layout.blocks.append(AABB(1.5, 0, 0, 0.3, 4, 3))
        self.assertTrue(self.sim.use_power("pulse", (0, 0, 0), (0, 1)))
        self.assertFalse(near.alive)
        self.assertEqual(blocked.hp, blocked.max_hp)
        self.assertFalse(self.sim.use_power("pulse", (0, 0, 0), (0, 1)))
        self.assertEqual(self.sim.score.points, 200)  # activation + power kill

    def test_melee_cannot_hit_through_wall_or_across_height(self):
        enemy = self.add_enemy(position=(0.95, 0, 0))
        enemy.attack_timer = 0
        self.layout.blocks.append(AABB(0.45, 0, 0, 0.15, 4, 3))
        self.sim.update(0.05, (0, 0, 0))
        self.assertEqual(self.damage_events(), [])
        self.layout.blocks.clear()
        enemy.x = 0.5
        self.sim.update(0.05, (0, 0, 4))
        self.assertEqual(self.damage_events(), [])

    def test_melee_attacks_and_cooldown(self):
        enemy = self.add_enemy(position=(0, 0.9, 0))
        enemy.attack_timer = 0
        self.sim.update(0.05, (0, 0, 0))
        self.sim.update(0.05, (0, 0, 0))
        self.assertEqual(len(self.damage_events()), 1)
        self.assertEqual(self.damage_events()[0]["amount"], enemy.damage)

    def test_dash_temporarily_protects_player(self):
        enemy = self.add_enemy(position=(0, 0.9, 0))
        enemy.attack_timer = 0
        self.sim.use_power("dash", (0, 0, 0), (0, 1))
        self.sim.update(0.05, (0, 0, 0))
        self.assertEqual(self.damage_events(), [])

    def test_fast_projectile_hits_between_frames(self):
        projectile = Projectile(1, -5, 0, 1, 100, 0, 0, 12)
        self.sim.projectiles.append(projectile)
        self.sim.update(0.1, (0, 0, 0))
        self.assertFalse(projectile.alive)
        self.assertEqual(len(self.damage_events()), 1)

    def test_wall_blocks_swept_projectile(self):
        self.layout.blocks.append(AABB(-2, 0, 0, 0.1, 4, 3))
        projectile = Projectile(1, -5, 0, 1, 100, 0, 0, 12)
        self.sim.projectiles.append(projectile)
        self.sim.update(0.1, (0, 0, 0))
        self.assertFalse(projectile.alive)
        self.assertEqual(self.damage_events(), [])
        self.assertLess(projectile.x, -1.9)

    def test_projectile_above_player_misses(self):
        projectile = Projectile(1, -5, 0, 4, 100, 0, 0, 12)
        self.sim.projectiles.append(projectile)
        self.sim.update(0.1, (0, 0, 0))
        self.assertTrue(projectile.alive)
        self.assertEqual(self.damage_events(), [])

    def test_crouching_player_can_dodge_high_projectile(self):
        self.sim.player_height = 0.9
        projectile = Projectile(1, -5, 0, 1.5, 100, 0, 0, 12)
        self.sim.projectiles.append(projectile)
        self.sim.update(0.1, (0, 0, 0))
        self.assertTrue(projectile.alive)
        self.assertEqual(self.damage_events(), [])

    def test_low_cover_navigation_does_not_follow_chest_sightline(self):
        self.layout.blocks.append(AABB(0, 0, 0, 3, 1, 1.0))
        enemy = self.add_enemy(position=(0, -2.5, 0))
        for _ in range(100):
            self.sim.update(0.1, (0, 3, 0))
        self.assertGreater(enemy.y, 1.0)
        self.assertLess(math.hypot(enemy.x, enemy.y - 3), 2)

    def test_ranged_demon_fires_and_elite_charges(self):
        ranged = self.add_enemy("ranged", (0, 10, 0))
        ranged.attack_timer = 0
        elite = self.add_enemy("elite", (7, 0, 0))
        elite.special_timer = 0
        self.sim.update(0.05, (0, 0, 0))
        self.assertEqual(len(self.sim.projectiles), 1)
        self.assertGreater(elite.charge_time, 0)
        self.assertLess(elite.x, 6.7)

    def test_death_freezes_cooldowns_and_enemies(self):
        enemy = self.add_enemy()
        self.sim.use_power("vision", (0, 0, 0), (0, 1))
        self.sim.update(10, (0, 0, 0), player_alive=False)
        self.assertEqual(self.sim.powers["vision"].cooldown, 18)
        self.assertEqual(enemy.y, 3)

    def test_reset_clears_every_round_state(self):
        self.add_enemy()
        self.sim.score.record_kill()
        self.sim.use_power("fury", (0, 0, 0), (0, 1))
        self.sim.reset()
        self.assertEqual(self.sim.enemies, [])
        self.assertEqual(self.sim.score.points, 0)
        self.assertEqual(self.sim.waves.round, 0)
        self.assertEqual(self.sim.powers["fury"].cooldown, 0)

    def test_ground_enemy_climbs_gallery_stairs(self):
        for side in (-1, 1):
            with self.subTest(side=side):
                sim = Simulation(ArenaLayout())
                sim.waves.intermission = 10000
                enemy = make_enemy(1, "heavy", (0, -15, 0))
                sim.enemies.append(enemy)
                target = (side * 15.7, 0, 1.8)
                for _ in range(240):
                    sim.update(0.1, target)
                self.assertAlmostEqual(enemy.z, 1.8)
                self.assertLess(math.hypot(enemy.x - target[0], enemy.y - target[1]), 2)


class WaveTests(unittest.TestCase):
    def test_counts_scale_without_unbounded_crowds(self):
        self.assertEqual([WaveManager.count_for_round(n) for n in (1, 2, 3)], [5, 8, 12])
        self.assertEqual(WaveManager.count_for_round(10000), 90)
        small = make_enemy(1, "basic", (0, 0, 0), 1)
        high = make_enemy(2, "basic", (0, 0, 0), 10000)
        self.assertGreater(high.hp, small.hp)
        self.assertGreater(high.damage, small.damage)
        self.assertLessEqual(high.speed, small.speed * 1.65)

    def test_alive_cap_leaves_pending_enemies(self):
        spawns = SpawnManager(EmptyArena(), random.Random(1))
        spawns.enqueue(10, 40)
        self.assertIsNone(spawns.update(2, (0, 0, 0), 28))
        self.assertEqual(len(spawns.pending), 40)
        self.assertIsNotNone(spawns.update(0.1, (0, 0, 0), 27))
        self.assertEqual(len(spawns.pending), 39)

    def test_chapel_spawns_are_on_ground_under_roof(self):
        layout = ArenaLayout()
        layout.spawn_points = [(0, 23)]
        spawns = SpawnManager(layout, random.Random(1))
        spawns.enqueue(1, 1)
        enemy = spawns.update(1, (0, 0, 0), 0)
        self.assertEqual(enemy.z, 0)
        self.assertTrue(layout.walkable(enemy.x, enemy.y, enemy.radius))

    def test_wave_clear_is_once_and_next_round_waits(self):
        sim = Simulation(EmptyArena())
        for _ in range(60):
            sim.update(0.1, (0, 0, 0))
            for enemy in sim.enemies:
                sim.hit(enemy, 100000)
        sim.update(0.1, (0, 0, 0))
        clears = [event for event in sim.events if event["type"] == "wave_clear"]
        self.assertEqual(len(clears), 1)
        self.assertEqual(sim.waves.round, 1)
        self.assertGreater(sim.waves.intermission, 0)
        sim.update(6, (0, 0, 0))
        self.assertEqual(sim.waves.round, 2)
        self.assertEqual(sim.waves.remaining, 8)


if __name__ == "__main__":
    unittest.main()

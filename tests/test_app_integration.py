"""Offscreen integration coverage through the actual application methods.

One shared ShowBase avoids graphics-context churn. The normal task loop never
runs: each test manually advances fixed 20 ms ticks without OS mouse input.
Scores are patched in memory, so running the suite never changes user records.
"""
from argparse import Namespace
import random
import unittest
from unittest.mock import patch

from game import config
from game.enemies.enemy import Projectile, STATS, make_enemy
from game.world.layout import AABB


class AppIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from panda3d.core import ClockObject, loadPrcFileData
        loadPrcFileData("integration-tests", "\n".join((
            "window-type offscreen", "win-size 640 360", "audio-library-name null",
            "sync-video false", "notify-level warning", "default-directnotify-level warning",
            "show-frame-rate-meter false", "framebuffer-multisample false",
        )))
        from game.app import NocturneApp
        cls.save_patch = patch("game.app.save_record")
        cls.save_mock = cls.save_patch.start()
        cls.load_patch = patch("game.app.load_record", return_value=0)
        cls.load_patch.start()
        cls.clock = ClockObject.getGlobalClock()
        cls.old_clock_mode = cls.clock.getMode()
        cls.clock.setMode(ClockObject.MNonRealTime)
        cls.clock.setDt(0.02)
        args = Namespace(quality="low", mute=True, seed=7, smoke_test=False,
                         offscreen=True, frames=1000000, screenshot=None, menu_screenshot=None)
        try:
            cls.app = NocturneApp(args)
            cls.app.taskMgr.remove("nocturne-frame")
        except Exception:
            cls.load_patch.stop()
            cls.save_patch.stop()
            cls.clock.setMode(cls.old_clock_mode)
            raise
        cls.task = Namespace(cont="continue", done="done")

    @classmethod
    def tearDownClass(cls):
        try:
            cls.app.quit_game()
        finally:
            cls.load_patch.stop()
            cls.save_patch.stop()
            cls.clock.setMode(cls.old_clock_mode)

    def setUp(self):
        self.app.start_game()
        self.app.sim.waves.intermission = 10000  # Tests explicitly introduce threats.
        self.app.rng = random.Random(7)
        self.save_mock.reset_mock()
        self.advance(20)  # Settle the equip transition and initial camera pose.

    def advance(self, count=1):
        for _ in range(count):
            self.clock.setDt(0.02)
            self.assertEqual(self.app.tick(self.task), self.task.cont)

    def add_enemy(self, kind="basic", position=(0, -10, 0)):
        enemy = make_enemy(len(self.app.sim.enemies) + 1, kind, position)
        self.app.sim.enemies.append(enemy)
        self.app.sim.waves.remaining += 1
        return enemy

    def test_pause_freezes_gameplay_and_resume_continues(self):
        app = self.app
        enemy = self.add_enemy()
        app.weapon.ammo -= 3
        app.reload()
        app.power("fury")
        app.key("w", True)
        self.advance(3)
        app.pause_game()
        before = (app.elapsed, app.sim.elapsed, app.player.movement.pos, enemy.x, enemy.y,
                  app.weapon.reload_remaining, app.sim.powers["fury"].cooldown,
                  app.health, app.sim.score.points)
        app.trigger(True)
        app.power("pulse")
        self.advance(50)
        after = (app.elapsed, app.sim.elapsed, app.player.movement.pos, enemy.x, enemy.y,
                 app.weapon.reload_remaining, app.sim.powers["fury"].cooldown,
                 app.health, app.sim.score.points)
        self.assertEqual(before, after)
        self.assertFalse(app.firing)
        self.assertFalse(app.player.captured)
        self.assertEqual(app.hud.mode, "paused")
        app.resume_game()
        self.advance()
        self.assertGreater(app.elapsed, before[0])
        self.assertLess(app.weapon.reload_remaining, before[5])

    def test_lethal_damage_then_restart_resets_game_state(self):
        app = self.app
        enemy = self.add_enemy()
        app.sim.score.points = 900
        app.sim.projectiles.append(Projectile(1, 10, 10, 1, 0, 1, 0, 10))
        app.renderer.update(app.sim, app.elapsed, app.player.movement.pos)
        app.weapon.ammo = 2
        app.reload()
        app.power("fury")
        app.sim.events.append({"type": "damage", "amount": 1000})
        # A kill or wave reward in the lethal frame must not resurrect the player.
        app.sim.events.append({"type": "kill", "enemy": enemy, "headshot": False, "points": 100})
        app.sim.events.append({"type": "wave_clear", "round": 1})
        app.process_events()
        self.assertEqual(app.health, 0)
        self.assertEqual(app.mode, "dead")
        self.assertEqual(app.hud.mode, "dead")
        self.assertTrue(app.weapon_view.root.isHidden())
        self.save_mock.assert_called_once()
        recorded = app.high_score
        app.enter()
        self.assertEqual(app.mode, "playing")
        self.assertEqual(app.hud.mode, "playing")
        self.assertEqual(app.health, config.MAX_HEALTH)
        self.assertEqual(app.sim.score.points, 0)
        self.assertEqual(app.sim.waves.round, 0)
        self.assertEqual(app.sim.enemies, [])
        self.assertEqual(app.sim.projectiles, [])
        self.assertEqual(app.renderer.enemies, {})
        self.assertEqual(app.renderer.projectiles, {})
        self.assertEqual(app.high_score, recorded)
        self.assertFalse(app.weapon_view.root.isHidden())
        for weapon in app.weapons:
            self.assertEqual(weapon.ammo, weapon.config.magazine)
            self.assertEqual(weapon.reserve, weapon.config.reserve)
            self.assertFalse(weapon.reloading)
        self.assertTrue(all(power.cooldown == power.active == 0 for power in app.sim.powers.values()))

    def test_weapon_switch_cancels_reload_without_free_ammo(self):
        app = self.app
        pistol = app.weapon
        pistol.ammo = 2
        reserve = pistol.reserve
        app.reload()
        self.advance(8)
        self.assertTrue(pistol.reloading)
        app.equip(1)
        self.assertFalse(pistol.reloading)
        self.assertEqual(app.weapon.config.key, "rifle")
        self.assertEqual(app.weapon_view.current_key, "rifle")
        self.advance(80)
        app.equip(0)
        self.assertEqual((pistol.ammo, pistol.reserve), (2, reserve))

    def test_ads_interpolates_camera_and_weapon_alignment(self):
        app = self.app
        initial_fov = app.player.fov
        initial_x = app.weapon_view.root.getX()
        app.aim(True)
        self.advance()
        self.assertGreater(app.player.ads, 0)
        self.assertLess(app.player.ads, 1)
        self.assertLess(app.player.fov, initial_fov)
        self.assertGreater(app.player.fov, config.ADS_FOV)
        self.advance(60)
        self.assertGreater(app.player.ads, 0.99)
        self.assertAlmostEqual(app.player.fov, config.ADS_FOV, delta=0.02)
        self.assertAlmostEqual(app.camLens.getHfov(), config.ADS_FOV, delta=0.02)
        self.assertLess(abs(app.weapon_view.root.getX()), initial_x * 0.05)
        app.aim(False)
        self.advance(60)
        self.assertAlmostEqual(app.player.fov, config.FOV, delta=0.02)

    def test_all_enemy_kinds_render_and_vision_marks_them(self):
        app = self.app
        for index, kind in enumerate(STATS):
            self.add_enemy(kind, ((index - 2) * 3, -8, 0))
        self.advance()
        self.assertEqual(len(app.renderer.enemies), 5)
        self.assertTrue(all(not visual.root.isEmpty() for visual in app.renderer.enemies.values()))
        self.assertTrue(all(visual.marker.isHidden() for visual in app.renderer.enemies.values()))
        app.power("vision")
        self.advance()
        self.assertTrue(all(not visual.marker.isHidden() for visual in app.renderer.enemies.values()))
        app.graphicsEngine.renderFrame()
        app.graphicsEngine.renderFrame()
        self.assertGreater(app.win.getXSize(), 0)
        for enemy in app.sim.enemies:
            enemy.alive = False
        self.advance()
        self.assertEqual(app.renderer.enemies, {})

    def test_dash_moves_player_and_pulse_damages_nearby_enemy(self):
        app = self.app
        start_y = app.player.movement.y
        app.power("dash")
        self.advance(8)
        self.assertGreater(app.player.movement.y, start_y + 3)
        self.assertGreater(app.sim.powers["dash"].cooldown, 3)
        x, y, z = app.player.movement.pos
        enemy = self.add_enemy(position=(x + 2, y, z))
        app.power("pulse")
        self.assertFalse(enemy.alive)
        app.process_events()
        self.assertGreater(app.sim.score.points, 100)
        self.assertGreater(app.sim.powers["pulse"].cooldown, 9)

    def test_fury_changes_actual_shot_damage_and_cadence(self):
        app = self.app
        target = self.add_enemy(position=(0, -11, 0))
        app.camera.setPos(0, -17, 1)
        app.camera.setHpr(0, 0, 0)
        app.player.ads = 1
        app.fire()
        normal_damage = target.max_hp - target.hp
        normal_cooldown = app.weapon.cooldown
        target.hp = target.max_hp
        app.weapon.cooldown = 0
        app.power("fury")
        app.fire()
        fury_damage = target.max_hp - target.hp
        self.assertAlmostEqual(fury_damage, normal_damage * 1.65, places=5)
        self.assertAlmostEqual(app.weapon.cooldown, normal_cooldown / 1.35, places=5)

    def test_fire_respects_cover_and_awards_headshot_kill(self):
        app = self.app
        target = self.add_enemy(position=(0, -11, 0))
        target.hp = 50
        app.camera.setPos(0, -17, target.height * 0.9)
        app.camera.setHpr(0, 0, 0)
        app.player.ads = 1
        blocker = AABB(0, -14, 0, 4, 0.3, 3)
        app.layout.blocks.append(blocker)
        try:
            app.fire()
            self.assertEqual(target.hp, 50)
            self.assertEqual(app.sim.score.points, 0)
        finally:
            app.layout.blocks.remove(blocker)
        app.weapon.cooldown = 0
        app.fire()
        self.assertFalse(target.alive)
        self.assertEqual(app.sim.score.points, 250)
        self.assertEqual(app.sim.score.headshots, 1)
        app.process_events()
        self.assertIn("CABEZA", app.toast)
        self.assertGreater(app.hitmarker, 0)


if __name__ == "__main__":
    unittest.main()

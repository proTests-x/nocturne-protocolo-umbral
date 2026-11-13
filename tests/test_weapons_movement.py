import unittest
from game.weapons import LOADOUT
from game.weapons.weapon import Weapon
from game.player.movement import Movement


class OpenLayout:
    def move(self, x, y, z, dx, dy, **kwargs):
        return x + dx, y + dy
    def floor_height(self, x, y, ceiling=999):
        return 0


class WeaponTests(unittest.TestCase):
    def test_ammo_and_rate_of_fire(self):
        for config in LOADOUT:
            weapon = Weapon(config)
            self.assertTrue(weapon.fire())
            self.assertFalse(weapon.fire())
            self.assertEqual(weapon.ammo, config.magazine - 1)
            weapon.update(config.interval)
            self.assertTrue(weapon.fire())

    def test_reload_conserves_ammo_and_cancel_does_not_grant_ammo(self):
        weapon = Weapon(LOADOUT[0])
        weapon.ammo = 1
        weapon.reserve = 3
        self.assertTrue(weapon.reload())
        self.assertFalse(weapon.fire())
        weapon.update(0.4)
        weapon.cancel_reload()
        self.assertEqual((weapon.ammo, weapon.reserve), (1, 3))
        weapon.reload()
        weapon.update(2)
        self.assertEqual((weapon.ammo, weapon.reserve), (4, 0))
        self.assertFalse(weapon.reload())


class MovementTests(unittest.TestCase):
    def test_diagonal_is_normalized(self):
        a, b = Movement(OpenLayout()), Movement(OpenLayout())
        for _ in range(100):
            a.update(.01, {'w': True}, 0)
            b.update(.01, {'w': True, 'd': True}, 0)
        self.assertAlmostEqual(a.speed, b.speed, places=5)

    def test_jump_lands_and_slide_requires_sprint(self):
        m = Movement(OpenLayout())
        m.jump()
        m.update(.2, {}, 0)
        self.assertGreater(m.z, 0)
        m.update(1, {}, 0)
        self.assertEqual(m.z, 0)
        self.assertTrue(m.grounded)
        m.update(.2, {'control': True}, 0)
        self.assertEqual(m.slide_remaining, 0)
        m.update(1, {'w': True, 'shift': True}, 0)
        m.update(.01, {'w': True, 'shift': True, 'control': True}, 0)
        self.assertGreater(m.slide_remaining, .7)

    def test_dash_and_frame_rate_stability(self):
        a, b = Movement(OpenLayout()), Movement(OpenLayout())
        for m in (a,b):
            m.dash((0,1))
        for _ in range(20):
            a.update(.01, {}, 0)
        for _ in range(4):
            b.update(.05, {}, 0)
        self.assertAlmostEqual(a.y, b.y, places=4)


if __name__ == '__main__':
    unittest.main()

"""Original procedural weapon models and continuous animation layers."""
import math
from panda3d.core import PointLight, BitMask32
from game.player.movement import approach
from game.world.geometry import box, cylinder


class WeaponView:
    def __init__(self, base):
        self.base = base
        self.root = base.camera.attachNewNode('first-person-weapon')
        self.root.setLightOff(1)
        self.root.setFogOff(1)
        self.root.setShaderOff(1)
        # A separate depth-cleared pass keeps the weapon out of walls while
        # preserving self-occlusion (the muzzle must not draw over the receiver).
        base.cam.node().setCameraMask(BitMask32.bit(0))
        base.render.hide(BitMask32.bit(1))
        self.root.hide(BitMask32.bit(0))
        self.root.hide(BitMask32.bit(3))
        self.root.showThrough(BitMask32.bit(1))
        self.view_camera = base.makeCamera(base.win, sort=5, scene=base.render,
                                          lens=base.camLens, clearDepth=True,
                                          camName='weapon-camera', mask=BitMask32.bit(1))
        self.kick = self.flash_time = self.switch_time = 0.0
        self.current_key = None
        self.light = PointLight('muzzle-light')
        self.light.setColor((1, .58, .22, 1))
        self.light.setAttenuation((1, 0, .5))
        self.light_np = base.camera.attachNewNode(self.light)
        self.light_np.setPos(.2, .6, -.05)
        self.muzzle = None

    def equip(self, config):
        for child in self.root.getChildren():
            child.removeNode()
        self.current_key = config.key
        self.switch_time = .32
        self.kick = 0
        dark = (.075, .10, .13, 1)
        metal = (.22, .29, .34, 1)
        edge = (.38, .46, .50, 1)
        brass = (.57, .40, .22, 1)
        glow = (.23, .92, 1, 1)
        long = config.key != 'pistol'
        length = .53 if long else .29
        width = .095 if config.key == 'shotgun' else .075
        box(self.root, 'receiver', (0, .15, 0), (width*1.75, length*.67, .13), dark)
        box(self.root, 'slide', (0, .16, .073), (width*1.57, length*.78, .052), metal)
        box(self.root, 'rail', (0, .13, .109), (.032, length*.7, .018), edge)
        grip = box(self.root, 'grip', (0, .025, -.11), (.076, .10, .19), dark)
        grip.setP(-16)
        for z in (-.17, -.13, -.09):
            box(self.root, 'grip-cut', (.04, .016, z), (.006, .066, .008), metal)
        barrel = cylinder(self.root, 'barrel', (0, length*.70, .043), .035, length*.61, metal, 12)
        barrel.setP(90)
        muzzle_y = length * 1.02
        rim = cylinder(self.root, 'muzzle-rim', (0, muzzle_y, .043), .044, .031, edge, 12)
        rim.setP(90)
        bore = cylinder(self.root, 'bore', (0, muzzle_y+.018, .043), .029, .004, (.009,.011,.015,1), 12)
        bore.setP(90)
        if long:
            box(self.root, 'handguard', (0, .32, .025), (.15, .23, .11), dark)
            for y in (.24, .28, .32, .36, .4):
                box(self.root, 'rib', (.079, y, .03), (.009, .019, .08), edge)
            box(self.root, 'stock', (0, -.105, -.015), (.13, .17, .13), metal)
            if config.key == 'rifle':
                magazine = box(self.root, 'magazine', (0, .15, -.16), (.066, .115, .22), metal)
                magazine.setP(-10)
                box(self.root, 'magazine-band', (0, .14, -.16), (.070, .118, .023), brass)
            else:
                for y in (.06, .105, .15, .195):
                    shell = cylinder(self.root, 'side-shell', (.09,y,-.02), .017,.072,(.54,.13,.14,1),8)
                    shell.setP(90)
        box(self.root, 'ejection-port', (.07, .12, .056), (.006, .074, .026), (.015,.024,.03,1))
        box(self.root, 'serial-plate', (.074, .055, .021), (.007, .064, .025), brass)
        for y in (.02,.047,.074):
            box(self.root, 'luminous-tick', (.079,y,.027), (.008,.006,.012), glow)
        for x in (-.037,.037):
            box(self.root, 'rear-sight', (x,-.015,.144), (.018,.025,.055), dark)
            box(self.root, 'rear-lumen', (x,-.029,.157), (.009,.004,.009), glow)
        box(self.root, 'front-sight', (0,length*.73,.144), (.014,.025,.06), metal)
        box(self.root, 'front-lumen', (0,length*.73-.014,.165), (.007,.004,.012), glow)
        # Sleeved arms remain attached to the animated weapon, without external assets.
        box(self.root, 'right-glove', (.025,-.005,-.16), (.11,.13,.13), (.14,.17,.19,1))
        sleeve = box(self.root, 'right-sleeve', (.12,-.19,-.25), (.145,.36,.15), (.028,.045,.063,1))
        sleeve.setH(-19)
        if long:
            box(self.root, 'left-glove', (-.035,.30,-.095), (.13,.13,.10), (.13,.16,.18,1))
            sleeve = box(self.root, 'left-sleeve', (-.17,.10,-.18), (.15,.40,.16), (.033,.05,.07,1))
            sleeve.setH(30)
        self.muzzle = self.root.attachNewNode('muzzle-origin')
        self.muzzle.setPos(0, muzzle_y+.035, .043)
        self.flash = self.muzzle.attachNewNode('flash')
        for angle in (0,45,90):
            node = box(self.flash, 'flash-blade', (0,.055,0), (.085,.16,.011), (1,.81,.38,1))
            node.setR(angle)
        self.flash.hide()

    def fire(self, recoil):
        self.kick = min(.14, self.kick + .027 + recoil * .012)
        self.flash_time = .05
        self.flash.show()
        self.base.render.setLight(self.light_np)

    def update(self, dt, player, weapon):
        self.kick = approach(self.kick, 0, 17, dt)
        self.flash_time -= dt
        if self.flash_time <= 0:
            self.flash.hide()
            self.base.render.clearLight(self.light_np)
        self.switch_time = max(0, self.switch_time-dt)
        m, ads = player.movement, player.ads
        bob = min(1,m.speed/6) * (1-ads*.85) * (1 if m.grounded else .12)
        phase = m.bob_phase
        x = .29 * (1-ads) + math.sin(phase)*.012*bob
        y = .51 + ads*.05 - self.kick
        z = -.29*(1-ads) - .159*ads + math.cos(phase*2)*.008*bob
        roll, pitch = -3*(1-ads), self.kick*70
        if m.sprinting:
            z -= .065
            roll += 9
            pitch -= 13
        if m.slide_remaining:
            roll -= 12
            z -= .05
        z -= .35 * (self.switch_time/.32)**2
        z -= min(.07,abs(m.vz)*.008)
        if weapon.reloading:
            progress = weapon.reload_progress
            motion = math.sin(progress*math.pi)
            z -= motion*.19
            y -= motion*.13
            x -= motion*.1
            roll -= motion*43
            pitch -= motion*18
            # Small insertion impulse late in the reload.
            y += math.sin(max(0,progress-.65)*math.pi/.35)*.025
        self.root.setPos(x,y,z)
        self.root.setHpr(0,pitch,roll)

    def destroy(self):
        self.base.render.clearLight(self.light_np)
        self.light_np.removeNode()
        self.root.removeNode()
        self.view_camera.removeNode()

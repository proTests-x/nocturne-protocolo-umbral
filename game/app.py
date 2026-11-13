"""Application coordinator: input, simulation, visuals and scene lifetime."""
import json
import math
import random
import time
from pathlib import Path

from direct.showbase.ShowBase import ShowBase
from panda3d.core import Vec3, Filename, ClockObject, ModifierButtons

from game import config
from game.audio.sound import SoundSystem
from game.player.controller import PlayerController
from game.rendering import CombatRenderer
from game.systems.persistence import load_record, save_record
from game.systems.simulation import Simulation
from game.ui.hud import HUD
from game.weapons import LOADOUT
from game.weapons.ballistics import trace
from game.weapons.weapon import Weapon
from game.weapons.viewmodel import WeaponView
from game.world.arena import Arena
from game.world.effects import Effects
from game.world.layout import ArenaLayout


class NocturneApp(ShowBase):
    def __init__(self, args):
        super().__init__()
        self.args = args
        self.disableMouse()
        self.setBackgroundColor(.015,.023,.044,1)
        self.camLens.setNearFar(.035, 180)
        self.mode = 'menu'
        self.elapsed = self.visual_time = 0.0
        self.frame = 0
        self.muted = args.mute
        self.high_score = load_record()
        self.rng = random.Random(args.seed)
        self.layout = ArenaLayout()
        self.arena = Arena(self, self.layout, quality=args.quality)
        self.player = PlayerController(self, self.layout)
        self.sim = Simulation(self.layout, seed=args.seed if args.seed is not None else random.randrange(2**30))
        self.renderer = CombatRenderer(self)
        self.effects = Effects(self)
        self.audio = SoundSystem(self, enabled=not args.mute)
        self.weapons = [Weapon(c) for c in LOADOUT]
        self.equipped = 0
        self.weapon_view = WeaponView(self)
        self.weapon_view.equip(self.weapon.config)
        self.weapon_view.root.hide()
        self.health = config.MAX_HEALTH
        self.hitmarker = self.damage_flash = self.invulnerability = 0.0
        self.toast = ''
        self.toast_time = 0.0
        self.firing = self.aiming = False
        self.shot_pressed = False
        self.step_timer = 0
        self.show_fps = False
        self.trail_timer = 0
        self.metrics = {'shots':0,'hits':0,'kills':0,'powers':0,'reloads':0,'waves':0,'damage_events':0}
        self.hud = HUD(self)
        self.hud.set_mode('menu', self.state())
        self._bind()
        self.taskMgr.add(self.tick, 'nocturne-frame')
        self._wall_start = time.perf_counter()
        if args.smoke_test:
            self.start_game()

    @property
    def weapon(self):
        return self.weapons[self.equipped]

    def _bind(self):
        # Keep Shift/Ctrl as independent controls. Panda's default modifier
        # prefixes otherwise turn "w" into "shift-w" and break sprint input.
        if self.mouseWatcherNode:
            self.mouseWatcherNode.setModifierButtons(ModifierButtons())
        for thrower in self.buttonThrowers or []:
            thrower.node().setModifierButtons(ModifierButtons())
        for key in ('w','a','s','d','shift','control','c'):
            self.accept(key, self.key, [key, True])
            self.accept(key+'-up', self.key, [key, False])
        self.accept('space', self.jump)
        self.accept('mouse1', self.trigger, [True])
        self.accept('mouse1-up', self.trigger, [False])
        self.accept('mouse3', self.aim, [True])
        self.accept('mouse3-up', self.aim, [False])
        self.accept('r', self.reload)
        self.accept('escape', self.escape)
        self.accept('enter', self.enter)
        self.accept('m', self.toggle_mute)
        self.accept('f3', self.toggle_fps)
        self.accept('window-event', self.window_event)
        for i in range(3):
            self.accept(str(i+1), self.equip, [i])
        self.accept('wheel_up', self.cycle_weapon, [1])
        self.accept('wheel_down', self.cycle_weapon, [-1])
        for key,name in (('q','dash'),('e','pulse'),('f','vision'),('x','fury')):
            self.accept(key, self.power, [name])

    def key(self, key, pressed):
        if self.mode == 'playing':
            self.player.keys[key] = pressed

    def trigger(self, pressed):
        if self.mode != 'playing':
            return
        self.firing = pressed
        if pressed:
            self.shot_pressed = True

    def aim(self, pressed):
        self.aiming = pressed and self.mode == 'playing'

    def jump(self):
        if self.mode == 'playing':
            self.player.movement.jump()

    def enter(self):
        if self.mode in ('menu','dead'):
            self.start_game()
        elif self.mode == 'paused':
            self.resume_game()

    def escape(self):
        if self.mode == 'playing':
            self.pause_game()
        elif self.mode == 'paused':
            self.resume_game()

    def start_game(self):
        self.sim.reset()
        self.renderer.clear()
        self.effects.clear()
        self.player.reset()
        self.weapons = [Weapon(c) for c in LOADOUT]
        self.equipped = 0
        self.weapon_view.equip(self.weapon.config)
        self.weapon_view.root.show()
        self.health = config.MAX_HEALTH
        self.hitmarker = self.damage_flash = self.invulnerability = 0.0
        self.elapsed = 0.0
        self.mode = 'playing'
        self.firing = self.aiming = self.shot_pressed = False
        self.player.capture(not self.args.smoke_test and not self.args.offscreen)
        self.hud.set_mode('playing', self.state())
        self.message('EL UMBRAL SE ABRE', 2.2)

    def pause_game(self):
        self.mode = 'paused'
        self.firing = self.aiming = self.shot_pressed = False
        self.player.capture(False)
        self.hud.set_mode('paused', self.state())

    def resume_game(self):
        self.mode = 'playing'
        self.player.capture(not self.args.smoke_test and not self.args.offscreen)
        self.hud.set_mode('playing', self.state())

    def window_event(self, window):
        if window != self.win or not hasattr(window,'getProperties'):
            return
        props=window.getProperties()
        if props.hasForeground() and not props.getForeground() and self.mode == 'playing' and not self.args.smoke_test:
            self.pause_game()

    def toggle_fps(self):
        self.show_fps = not self.show_fps

    def toggle_mute(self):
        self.muted = not self.muted
        self.audio.set_muted(self.muted)
        self.message('AUDIO SILENCIADO' if self.muted else 'AUDIO ACTIVADO', 1.5)

    def equip(self, index):
        if self.mode != 'playing' or index == self.equipped:
            return
        self.weapon.cancel_reload()
        self.equipped = index % len(self.weapons)
        self.weapon_view.equip(self.weapon.config)
        self.shot_pressed = False
        self.aiming = False

    def cycle_weapon(self, direction):
        self.equip((self.equipped+direction)%3)

    def reload(self):
        if self.mode == 'dead':
            self.start_game()
        elif self.mode == 'playing' and self.weapon.reload():
            self.audio.play('reload', .7)
            self.metrics['reloads'] += 1

    def power(self, name):
        if self.mode != 'playing':
            return
        if self.sim.use_power(name, self.player.movement.pos, self.player.forward):
            if name == 'dash':
                self.player.movement.dash(self.player.forward)
            self.metrics['powers'] += 1

    def message(self, text, duration=2.2):
        self.toast,self.toast_time=text,duration

    def fire(self):
        if self.weapon_view.switch_time > .08:
            return
        weapon = self.weapon
        fury = self.sim.powers['fury'].active > 0
        if not weapon.fire(fury):
            if weapon.ammo == 0 and not weapon.reloading:
                self.reload()
            return
        self.metrics['shots'] += 1
        self.audio.play(weapon.config.key, .85)
        self.weapon_view.fire(weapon.config.recoil)
        quat = self.camera.getQuat(self.render)
        forward,right,up = quat.getForward(),quat.getRight(),quat.getUp()
        origin=self.camera.getPos(self.render)
        muzzle=self.weapon_view.muzzle.getPos(self.render)
        self.effects.smoke(tuple(muzzle), count=3 if weapon.config.key=='shotgun' else 1)
        movement=self.player.movement
        spread=weapon.config.spread * (1-self.player.ads*.73)
        spread*=1.32 if movement.speed>4 else 1
        spread*=1.55 if not movement.grounded else 1
        for pellet in range(weapon.config.pellets):
            angle=self.rng.uniform(0,math.tau)
            radius=math.sqrt(self.rng.random())*math.tan(math.radians(spread))
            direction=forward+right*(math.cos(angle)*radius)+up*(math.sin(angle)*radius)
            direction.normalize()
            enemy,headshot,distance=trace(self.layout,self.sim.enemies,tuple(origin),tuple(direction),weapon.config.range)
            point=origin+direction*distance
            if pellet < 3:
                self.effects.tracer(tuple(muzzle),tuple(point),(1,.75,.37,1))
            if enemy is not None:
                damage=weapon.config.damage*(1.65 if headshot else 1)*(1.65 if fury else 1)
                if weapon.config.key=='shotgun':
                    damage*=max(.35,1-distance/60)
                self.sim.hit(enemy,damage,headshot=headshot)
                self.effects.burst(tuple(point),(1,.14,.28,1),count=5)
                self.hitmarker=.16
                self.metrics['hits']+=1
                if pellet==0:
                    self.audio.play('impact',.4)
            elif distance<weapon.config.range:
                self.effects.burst(tuple(point),(1,.66,.31,1),count=3)
                if pellet<2:
                    self.effects.impact(tuple(point),tuple(direction))
        self.player.recoil+=weapon.config.recoil*(1-self.player.ads*.35)

    def process_events(self):
        for event in self.sim.events:
            kind=event['type']
            if kind=='damage' and self.invulnerability<=0 and self.health>0:
                self.health=max(0,self.health-event['amount'])
                self.damage_flash=.8
                self.invulnerability=.28
                self.player.shake=1.2
                self.audio.play('hurt',.65)
                self.metrics['damage_events']+=1
            elif kind=='kill':
                enemy=event['enemy']
                self.effects.burst((enemy.x,enemy.y,enemy.z+enemy.height*.55),(1,.12,.3,1),count=16)
                self.audio.play('kill',.45)
                self.health=min(100,self.health+2) if self.health>0 else 0
                self.metrics['kills']+=1
                label='DISPARO A LA CABEZA' if event['headshot'] else 'EXORCISMO'
                self.message(f"{label}   +{event.get('points',100)}",1.2)
            elif kind=='spawn':
                enemy=event['enemy']
                self.effects.ring((enemy.x,enemy.y,enemy.z+.04),(1,.11,.25,1))
                if self.rng.random()<.3:
                    self.audio.play('roar',.28)
            elif kind=='wave':
                self.message(f"OLEADA {event['round']:02d}   /   SOBREVIVE",2.6)
                self.audio.play('wave',.65)
                self.metrics['waves']+=1
            elif kind=='wave_clear':
                self.health=min(100,self.health+22) if self.health>0 else 0
                for weapon in self.weapons:
                    weapon.replenish()
                self.message('UMBRAL SELLADO   /   +22 VIDA + MUNICION',3.6)
            elif kind=='power':
                name=event['name']
                self.audio.play(name,.75)
                pos=self.player.movement.pos
                self.effects.ring((pos[0],pos[1],pos[2]+.15),(.35,.35,1,1))
                self.effects.burst((pos[0],pos[1],pos[2]+.75),(.3,.55,1,1),count=24)
                if name=='pulse':
                    self.player.shake=1.4
        self.sim.events.clear()
        if self.health<=0 and self.mode=='playing':
            self.die()

    def die(self):
        self.mode='dead'
        self.firing=self.aiming=False
        self.player.capture(False)
        self.weapon_view.root.hide()
        self.high_score=max(self.high_score,self.sim.score.points)
        if not self.args.smoke_test:
            save_record(self.high_score)
        self.hud.set_mode('dead',self.state())

    def state(self):
        return {
            'health':self.health,'ammo':self.weapon.ammo,'reserve':self.weapon.reserve,
            'weapon':self.weapon.config.name,'score':self.sim.score.points,
            'high_score':max(self.high_score,self.sim.score.points),'combo':self.sim.score.combo,
            'round':self.sim.waves.round,'remaining':self.sim.waves.remaining,
            'intermission':self.sim.waves.intermission,
            'powers':{name:{'cooldown':p.cooldown,'active':p.active} for name,p in self.sim.powers.items()},
            'ads':self.player.ads,'reloading':self.weapon.reloading,
            'hitmarker':self.hitmarker,'damage_flash':self.damage_flash,
            'fps':ClockObject.getGlobalClock().getAverageFrameRate() if self.show_fps else 0,'toast':self.toast,
            'toast_time':self.toast_time,'elapsed':self.elapsed,
        }

    def _autoplay(self):
        """Smoke driver uses the same fire/equip/reload/power paths as input."""
        if self.frame in (150,350,550):
            self.equip((self.equipped+1)%3)
        if self.frame in (250,450,650):
            self.reload()
        if self.frame in (120,180,240,300):
            self.power(('vision','fury','dash','pulse')[(self.frame-120)//60])
        if self.frame==400:
            self.jump()
        enemies=[e for e in self.sim.enemies if e.alive]
        if enemies:
            position=self.camera.getPos(self.render)
            # Prefer visible targets so the integration exercise produces real hits.
            def rank(e):
                delta=Vec3(e.x-position.x,e.y-position.y,e.z+e.height*.84-position.z)
                distance=delta.length()
                wall=self.layout.raycast(tuple(position),tuple(delta),distance)
                return distance+(100 if wall is not None and wall<distance-.5 else 0)
            target=min(enemies,key=rank)
            dx,dy=target.x-position.x,target.y-position.y
            dz=target.z+target.height*.83-position.z
            self.player.yaw=-math.degrees(math.atan2(dx,dy))
            self.player.pitch=math.degrees(math.atan2(dz,math.hypot(dx,dy)))
            self.aiming=True
            self.firing=True
            self.shot_pressed=True

    def tick(self,task):
        self.frame+=1
        dt=1/60 if self.args.smoke_test or self.args.menu_screenshot else min(ClockObject.getGlobalClock().getDt(),.05)
        self.visual_time+=dt
        if self.mode=='playing':
            self.elapsed+=dt
            self.hitmarker=max(0,self.hitmarker-dt)
            self.damage_flash=max(0,self.damage_flash-dt*2.4)
            self.invulnerability=max(0,self.invulnerability-dt)
            self.toast_time=max(0,self.toast_time-dt)
            if self.args.smoke_test:
                self._autoplay()
            fury=self.sim.powers['fury'].active>0
            self.player.update(dt,self.aiming,fury,mouse=not self.args.smoke_test)
            for weapon in self.weapons:
                weapon.update(dt)
            self.weapon_view.update(dt,self.player,self.weapon)
            if (self.weapon.config.automatic and self.firing) or self.shot_pressed:
                self.fire()
            self.shot_pressed=False
            self.sim.player_height=self.player.movement.eye_height
            self.sim.update(dt,self.player.movement.pos)
            self.process_events()
            self.renderer.update(self.sim,self.elapsed,self.player.movement.pos)
            self.effects.update(dt)
            self.trail_timer-=dt
            if self.player.movement.dash_remaining>0 and self.trail_timer<=0:
                pos=self.player.movement.pos
                self.effects.smoke((pos[0],pos[1],pos[2]+.7),(.17,.10,.32,.45),count=3)
                self.trail_timer=.035
            self.step_timer-=dt
            m=self.player.movement
            if m.grounded and m.speed>1 and self.step_timer<=0 and not m.slide_remaining:
                self.audio.play('step',.25)
                self.step_timer=.29 if m.sprinting else .43
        elif self.mode=='menu':
            self.camera.setPos(0,-22,3.8)
            self.camera.setHpr(math.sin(self.visual_time*.09)*3,3,0)
            self.camLens.setFov(82)
        self.arena.update(dt,self.visual_time,self.player.movement.pos)
        self.audio.update(dt,in_combat=self.mode=='playing' and self.sim.waves.active)
        self.hud.update(self.state(),dt)
        if self.args.menu_screenshot and self.frame>=30:
            self.capture_to(self.args.menu_screenshot)
            self.quit_game()
            return task.done
        if self.args.smoke_test and self.frame>=self.args.frames:
            if self.args.screenshot:
                self.capture_to(self.args.screenshot)
            report={**self.metrics,'frames':self.frame,'round':self.sim.waves.round,
                    'score':self.sim.score.points,'health':self.health,'mode':self.mode,
                    'render_seconds':round(time.perf_counter()-self._wall_start,2)}
            print('SMOKE_RESULT '+json.dumps(report),flush=True)
            report_dir=Path(__file__).resolve().parents[1]/'artifacts'
            report_dir.mkdir(exist_ok=True)
            (report_dir/'smoke-result.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
            self.quit_game()
            return task.done
        return task.cont

    def capture_to(self,path):
        path=Path(path).resolve()
        path.parent.mkdir(parents=True,exist_ok=True)
        self.graphicsEngine.renderFrame()
        self.graphicsEngine.renderFrame()
        self.win.saveScreenshot(Filename.fromOsSpecific(str(path)))

    def quit_game(self):
        if not self.args.smoke_test and self.sim.score.points>self.high_score:
            self.high_score=self.sim.score.points
            save_record(self.high_score)
        self.player.capture(False)
        self.audio.destroy()
        self.taskMgr.stop()
        self.destroy()

    def userExit(self):
        """Window close uses the same cleanup and record path as the menu."""
        self.quit_game()

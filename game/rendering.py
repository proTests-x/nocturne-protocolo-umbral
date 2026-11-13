"""Visible, animated demon silhouettes and projectile rendering."""
import math
from game.world.geometry import box, cylinder, beam


PALETTES = {
    'basic': ((.22,.065,.085,1), (1,.17,.23,1)),
    'fast': ((.16,.095,.26,1), (.85,.3,1,1)),
    'heavy': ((.18,.20,.24,1), (1,.37,.13,1)),
    'ranged': ((.12,.14,.24,1), (.45,.54,1,1)),
    'elite': ((.25,.10,.15,1), (1,.68,.3,1)),
}


class EnemyVisual:
    def __init__(self, base, enemy):
        self.base = base
        self.root = base.render.attachNewNode(f'demon-{enemy.id}')
        self.body = self.root.attachNewNode('body')
        skin, glow = PALETTES[enemy.kind]
        r, h = enemy.radius, enemy.height
        chest = box(self.body,'armored-chest',(0,0,h*.57),(r*1.65,r*.95,h*.34),skin)
        chest.setH(8)
        box(self.body,'waist',(0,0,h*.36),(r*.9,r*.72,h*.17),(.055,.045,.075,1))
        box(self.body,'sternum',(0,r*.51,h*.58),(r*.25,.055,h*.27),glow).setLightOff(1)
        for x in (-1,1):
            for k in range(3):
                rib=box(self.body,'rib',(x*r*.39,r*.5,h*(.48+k*.08)),(r*.53,.06,.06),(.35,.29,.31,1))
                rib.setR(x*18)
        head = cylinder(self.body,'mask',(0,0,h*.85),r*.63,h*.27,(.35,.32,.34,1),5)
        head.setH(18)
        for side in (-1,1):
            box(self.body,'eye',(side*r*.24,r*.59,h*.90),(r*.25,.045,.06),glow).setLightOff(1)
            horn = cylinder(self.body,'horn',(side*r*.54,-.04,h*1.01),r*.105,h*.32,skin,3)
            horn.setR(side*24)
            shoulder=box(self.body,'pauldron',(side*r*.95,0,h*.65),(r*.64,r*1.2,h*.14),skin)
            shoulder.setR(side*20)
        self.arms, self.legs = [], []
        for side in (-1,1):
            arm = self.body.attachNewNode('arm-pivot')
            arm.setPos(side*r*.99,0,h*.62)
            box(arm,'forearm',(0,.04,-h*.18),(r*.38,r*.56,h*.35),skin)
            for claw in (-1,1):
                beam(arm,(claw*r*.14,.06,-h*.29),(claw*r*.18,.26,-h*.42),.045,glow)
            leg=self.root.attachNewNode('leg-pivot')
            leg.setPos(side*r*.42,0,h*.36)
            box(leg,'shin',(0,0,-h*.15),(r*.49,r*.64,h*.32),skin)
            box(leg,'foot',(0,.09,-h*.32),(r*.58,r*.98,h*.08),(.07,.05,.08,1))
            self.arms.append(arm)
            self.legs.append(leg)
        if enemy.kind in ('elite','heavy'):
            for x in (-1,0,1):
                spike=cylinder(self.body,'crown',(x*r*.6,0,h*1.10),.09,h*.35,glow,3)
                spike.setR(x*24)
        if enemy.kind == 'ranged':
            ring = cylinder(self.body,'halo',(0,-.13,h*.94),r*1.0,.035,glow,8)
            ring.setP(90)
            ring.setLightOff(1)
        self.marker = box(self.root,'vision-mark',(0,0,h*1.4),(.11,.11,.22),glow)
        self.marker.setLightOff(1)
        self.marker.setDepthTest(False)
        self.marker.setBin('fixed',20)
        self.marker.hide()

    def update(self, enemy, time, player_pos, vision=False):
        self.root.setPos(enemy.x,enemy.y,enemy.z)
        # Procedural creatures face along local +Y, matching their eye positions.
        dx,dy=player_pos[0]-enemy.x,player_pos[1]-enemy.y
        self.root.setH(-math.degrees(math.atan2(dx,dy)))
        pace=time*(11 if enemy.kind=='fast' else 5 if enemy.kind=='heavy' else 8)+enemy.id
        self.body.setZ(math.sin(pace*2)*.025)
        for i,(arm,leg) in enumerate(zip(self.arms,self.legs)):
            swing=math.sin(pace+i*math.pi)*24
            leg.setP(swing)
            arm.setP(-swing*.8-18)
        if enemy.hit_flash>0:
            self.root.setColorScale(2.5,1.7,1.7,1)
        elif vision:
            self.root.setColorScale(1.7,1.25,1.7,1)
        else:
            self.root.clearColorScale()
        if vision:
            self.marker.show()
        else:
            self.marker.hide()

    def destroy(self):
        self.root.removeNode()


class CombatRenderer:
    def __init__(self,base):
        self.base=base
        self.enemies={}
        self.projectiles={}

    def update(self,simulation,time,player_pos):
        living={e.id for e in simulation.enemies if e.alive}
        for ident in list(self.enemies):
            if ident not in living:
                self.enemies.pop(ident).destroy()
        vision=simulation.powers['vision'].active>0
        for enemy in simulation.enemies:
            if not enemy.alive:
                continue
            if enemy.id not in self.enemies:
                self.enemies[enemy.id]=EnemyVisual(self.base,enemy)
            self.enemies[enemy.id].update(enemy,time,player_pos,vision)
        live_projectiles={p.id for p in simulation.projectiles if p.alive}
        for ident in list(self.projectiles):
            if ident not in live_projectiles:
                self.projectiles.pop(ident).removeNode()
        for projectile in simulation.projectiles:
            if not projectile.alive:
                continue
            if projectile.id not in self.projectiles:
                node=box(self.base.render,'supernatural-projectile',(0,0,0),(.23,.23,.23),(.76,.24,1,1))
                node.setLightOff(1)
                self.projectiles[projectile.id]=node
            node=self.projectiles[projectile.id]
            node.setPos(projectile.x,projectile.y,projectile.z)
            node.setHpr(time*180,time*130,45)

    def clear(self):
        for visual in self.enemies.values():
            visual.destroy()
        for node in self.projectiles.values():
            node.removeNode()
        self.enemies.clear()
        self.projectiles.clear()

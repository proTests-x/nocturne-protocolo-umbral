"""Short-lived supernatural particles, hitscan tracers and power rings.

The spark mesh is shared and its NodePaths are reused. Active effect count
is capped even when a shotgun hits a crowd at full automatic fire rate.
"""
import math
import random

from panda3d.core import (
    Geom, GeomNode, GeomTriangles, GeomVertexData, GeomVertexFormat,
    GeomVertexWriter, LineSegs, TransparencyAttrib, Vec3,
)


def _spark_mesh():
    data = GeomVertexData("spark", GeomVertexFormat.getV3(), Geom.UHStatic)
    vertices = GeomVertexWriter(data, "vertex")
    for vertex in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
        vertices.addData3(*vertex)
    triangles = GeomTriangles(Geom.UHStatic)
    for a, b in ((0, 2), (2, 1), (1, 3), (3, 0)):
        triangles.addVertices(a, b, 4)
        triangles.addVertices(b, a, 5)
    geom = Geom(data)
    geom.addPrimitive(triangles)
    node = GeomNode("shared-spark")
    node.addGeom(geom)
    return node


def _smoke_mesh():
    """A radial alpha fan approximates soft smoke without bitmap assets."""
    data=GeomVertexData('smoke',GeomVertexFormat.getV3c4(),Geom.UHStatic)
    vertices=GeomVertexWriter(data,'vertex')
    colors=GeomVertexWriter(data,'color')
    vertices.addData3(0,0,0)
    colors.addData4(1,1,1,.4)
    for i in range(17):
        angle=math.tau*i/16
        vertices.addData3(math.cos(angle),0,math.sin(angle))
        colors.addData4(1,1,1,0)
    triangles=GeomTriangles(Geom.UHStatic)
    for i in range(1,17):
        triangles.addVertices(0,i,i+1)
    geom=Geom(data)
    geom.addPrimitive(triangles)
    node=GeomNode('smoke-disc')
    node.addGeom(geom)
    return node


class Effects:
    MAX_EFFECTS = 220
    MAX_FREE_SPARKS = 180

    def __init__(self, base, geometry=None):
        self.base = base
        self.root = base.render.attachNewNode("combat-effects")
        self.root.setLightOff(1)
        self.root.setShaderOff(1)
        self.root.setTransparency(TransparencyAttrib.MAlpha)
        self.root.setDepthWrite(False)
        self.root.setTwoSided(True)
        self.mesh = _spark_mesh()
        self.smoke_mesh = _smoke_mesh()
        self.active = []
        self.free = []
        self.rng = random.Random()

    def _release(self, effect):
        node = effect["node"]
        if effect["kind"] == "spark" and len(self.free) < self.MAX_FREE_SPARKS:
            node.detachNode()
            self.free.append(node)
        else:
            node.removeNode()

    def _append(self, effect):
        if len(self.active) >= self.MAX_EFFECTS:
            self._release(self.active.pop(0))
        self.active.append(effect)

    def burst(self, pos, color=(.85, .16, .35, 1), count=10):
        origin = Vec3(*pos)
        for _ in range(min(45, max(0, int(count)))):
            if self.free:
                node = self.free.pop()
                node.reparentTo(self.root)
            else:
                node = self.root.attachNewNode(self.mesh)
            velocity = Vec3(self.rng.uniform(-1, 1), self.rng.uniform(-1, 1),
                            self.rng.uniform(-.1, 1.5))
            velocity *= self.rng.uniform(1.2, 4.5)
            scale = self.rng.uniform(.025, .065)
            node.setPos(origin)
            node.setScale(scale, scale, scale * self.rng.uniform(1, 2.2))
            node.setColorScale(*color)
            lifetime = self.rng.uniform(.19, .48)
            self._append({"node": node, "kind": "spark", "life": lifetime,
                          "duration": lifetime, "velocity": velocity,
                          "color": color, "scale": scale})

    def tracer(self, start, end, color=(.62, .86, 1, .8)):
        lines = LineSegs("bullet-streak")
        lines.setThickness(1.6)
        lines.setColor(*color)
        lines.moveTo(Vec3(*start))
        lines.drawTo(Vec3(*end))
        node = self.root.attachNewNode(lines.create())
        self._append({"node": node, "kind": "tracer", "life": .055,
                      "duration": .055, "color": (1, 1, 1, 1)})

    def smoke(self,pos,color=(.52,.57,.64,.5),count=3):
        for _ in range(min(8,max(0,count))):
            node=self.root.attachNewNode(self.smoke_mesh)
            node.setPos(*pos)
            node.setBillboardPointEye()
            node.setScale(.07)
            node.setColorScale(*color)
            lifetime=self.rng.uniform(.45,.85)
            self._append({'node':node,'kind':'smoke','life':lifetime,'duration':lifetime,
                          'color':color,'velocity':Vec3(self.rng.uniform(-.18,.18),self.rng.uniform(-.15,.15),.45)})

    def impact(self,pos,direction):
        from game.world.geometry import cylinder
        axis=max(range(3),key=lambda i:abs(direction[i]))
        normal=[0,0,0]
        normal[axis]=-1 if direction[axis]>0 else 1
        point=tuple(pos[i]+normal[i]*.014 for i in range(3))
        node=cylinder(self.root,'bullet-scar',point,.045,.004,(.016,.018,.022,.9),8)
        if axis==0:
            node.setR(90)
        elif axis==1:
            node.setP(90)
        self._append({'node':node,'kind':'decal','life':4.0,'duration':4.0,'color':(1,1,1,1)})

    def ring(self, pos, color=(.3, .92, 1, .8)):
        lines = LineSegs("umbral-ring")
        lines.setThickness(2.6)
        lines.setColor(*color)
        # Two offset circles and broken inward spokes suggest a ritual seal.
        for radius in (1.0, .90):
            for i in range(49):
                angle = math.tau * i / 48
                point = (math.cos(angle) * radius, math.sin(angle) * radius, 0)
                lines.moveTo(*point) if i == 0 else lines.drawTo(*point)
        for i in range(12):
            angle = math.tau * i / 12
            lines.moveTo(math.cos(angle) * .74, math.sin(angle) * .74, 0)
            lines.drawTo(math.cos(angle) * .86, math.sin(angle) * .86, .04)
        node = self.root.attachNewNode(lines.create())
        node.setPos(Vec3(*pos) + Vec3(0, 0, .045))
        node.setScale(.18)
        self._append({"node": node, "kind": "ring", "life": .62,
                      "duration": .62, "color": (1, 1, 1, 1)})

    def update(self, dt):
        dt = min(.1, max(0, dt))
        alive = []
        for effect in self.active:
            effect["life"] -= dt
            if effect["life"] <= 0:
                self._release(effect)
                continue
            fraction = effect["life"] / effect["duration"]
            node = effect["node"]
            color = effect["color"]
            node.setColorScale(color[0], color[1], color[2], color[3] * fraction)
            if effect["kind"] == "spark":
                velocity = effect["velocity"]
                velocity.z -= dt * 5.5
                node.setPos(node.getPos() + velocity * dt)
                node.setScale(effect["scale"] * (.3 + fraction * .7))
            elif effect["kind"] == "ring":
                node.setScale(.18 + (1 - fraction) * 7.5)
            elif effect['kind']=='smoke':
                node.setPos(node.getPos()+effect['velocity']*dt)
                node.setScale(.07+(1-fraction)*.43)
            alive.append(effect)
        self.active = alive

    def clear(self):
        for effect in self.active:
            self._release(effect)
        self.active.clear()

    def destroy(self):
        self.clear()
        for node in self.free:
            node.removeNode()
        self.free.clear()
        self.root.removeNode()

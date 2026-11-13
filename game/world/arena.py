"""An original gothic industrial city, constructed entirely from geometry.

Every substantial in-bounds solid comes from ArenaLayout. Architectural
trim, neon, paint and rain are decorative; distant buildings are outside the
playable boundary. Opaque meshes are flattened for efficient batch drawing.
"""

import math
import random
from panda3d.core import (
    AmbientLight, BitMask32, DepthOffsetAttrib, DirectionalLight, Fog, Geom, GeomLines, GeomNode,
    GeomVertexData, GeomVertexFormat, GeomVertexWriter, PointLight,
    TextNode, TransparencyAttrib, Vec4,
)
from .geometry import box, cylinder, cone, beam


class Arena:
    def __init__(self, base, layout, quality="medium"):
        self.base, self.layout, self.quality = base, layout, quality
        self.root = base.render.attachNewNode("NOCTURNE — Saint Vesper court")
        self.solids = self.root.attachNewNode("static-masonry")
        self.neon = self.root.attachNewNode("emissive-detail")
        self.neon.setLightOff(1)
        self.water = self.root.attachNewNode("rainwater")
        self.water.setTransparency(TransparencyAttrib.MAlpha)
        self.water.setDepthWrite(False)
        self.water.setLightOff(1)
        self.shadows = self.root.attachNewNode("soft-contact-shadows")
        self.shadows.setTransparency(TransparencyAttrib.MAlpha)
        self.shadows.setDepthWrite(False)
        self.shadows.setLightOff(1)
        self.haze = self.root.attachNewNode("lantern-light-haze")
        self.haze.setTransparency(TransparencyAttrib.MAlpha)
        self.haze.setDepthWrite(False)
        self.haze.setLightOff(1)
        self.haze.setTwoSided(True)
        self.shadow_mask = BitMask32.bit(3)
        for decorative in (self.neon, self.water, self.shadows, self.haze):
            decorative.hide(self.shadow_mask)
        self.rng = random.Random(120419)
        self.lights = []
        self.fog = Fog("night-haze")
        self.fog.setColor(.018, .032, .062)
        self.fog.setExpDensity(.013 if quality != "low" else .011)
        base.render.setFog(self.fog)
        base.setBackgroundColor(.012, .021, .042, 1)
        self._lighting()
        self._ground()
        self._solid_arena()
        self._chapel()
        self._streets()
        self._skyline()
        self._moon()
        self._rain()
        self.solids.flattenStrong()
        self.neon.flattenStrong()
        self.water.flattenStrong()
        self.shadows.flattenStrong()
        self.haze.flattenStrong()

    def _lighting(self):
        ambient = AmbientLight("blue-hour-ambient")
        ambient.setColor((.43, .48, .62, 1))
        node = self.root.attachNewNode(ambient)
        self.base.render.setLight(node)
        self.lights.append(node)
        moon = DirectionalLight("moonlight")
        moon.setColor((.72, .83, 1.0, 1))
        self.shader_shadows = False
        if self.quality != "low":
            gsg = self.base.win.getGsg() if self.base.win else None
            if gsg and gsg.getSupportsBasicShaders():
                resolution = 2048 if self.quality == "high" else 1024
                moon.setShadowCaster(True, resolution, resolution)
                moon.getLens().setFilmSize(76, 76)
                moon.getLens().setNearFar(20, 125)
                moon.setCameraMask(self.shadow_mask)
                # Bias only the shadow pass; keep Panda's reversed culling
                # state and avoid moving real camera depth for decal surfaces.
                moon.setInitialState(moon.getInitialState().addAttrib(DepthOffsetAttrib.make(-2)))
                self.base.render.setShaderAuto()
                self.shader_shadows = True
        node = self.root.attachNewNode(moon)
        node.setPos(-32, 28, 62)
        node.lookAt(0, 0, 0)
        self.base.render.setLight(node)
        self.lights.append(node)
        # Two local lights are sufficient for warm/cold depth separation.
        for name, pos, color in [
            ("chapel-crimson", (0, 20, 4), (1.0, .12, .16, 1)),
            ("court-cyan", (0, -10, 5.5), (.1, .62, .92, 1)),
        ]:
            lamp = PointLight(name)
            lamp.setColor(color)
            lamp.setAttenuation((1, .05, .028))
            node = self.root.attachNewNode(lamp)
            node.setPos(*pos)
            self.base.render.setLight(node)
            self.lights.append(node)

    def _ground(self):
        box(self.solids, "courtyard-slab", (0, 0, -.22), (54, 54, .44), (.065, .087, .12, 1))
        # Dry stone seams and larger polished slabs: no texture downloads.
        for x in range(-25, 26, 2):
            for y in range(-25, 26, 2):
                value = self.rng.uniform(.8, 1.16)
                color = (.078 * value, .102 * value, .137 * value, 1)
                tile = box(self.solids, "flagstone", (x, y, .003), (1.965, 1.965, .006), color)
                tile.hide(self.shadow_mask)
        # Parallel industrial gutters point towards the entrance.
        for x in (-11.2, 11.2):
            box(self.solids, "storm-drain", (x, 0, .007), (.32, 49, .018), (.018, .027, .038, 1))
            for y in range(-24, 25):
                box(self.solids, "drain-bar", (x, y, .02), (.34, .07, .028), (.15, .2, .25, 1))
        for _ in range(34 if self.quality != "low" else 20):
            x, y = self.rng.uniform(-24, 24), self.rng.uniform(-24, 24)
            if not self.layout.walkable(x, y):
                continue
            wet = cylinder(self.water, "rain-pool", (x, y, .025), 1, .012,
                           (.10, .23, .34, .27), sides=12)
            wet.setScale(self.rng.uniform(.45, 2.5), self.rng.uniform(.35, 1.2), .012)
            wet.setH(self.rng.uniform(0, 360))
        # A faded ritual inlay stays legible in the central combat zone.
        for radius in (3.7, 4.0):
            for i in range(48):
                a, b = i * math.tau / 48, (i + .8) * math.tau / 48
                beam(self.neon, (math.sin(a) * radius, math.cos(a) * radius, .035),
                     (math.sin(b) * radius, math.cos(b) * radius, .035), .032,
                     (.15, .4, .48, 1))
        for i in range(8):
            a = i * math.tau / 8
            beam(self.neon, (math.sin(a) * 3.9, math.cos(a) * 3.9, .034),
                 (math.sin(a) * 4.4, math.cos(a) * 4.4, .034), .055, (.27, .49, .56, 1))

    def _solid_arena(self):
        palette = {
            "boundary": (.13, .17, .22, 1),
            "chapel_wall": (.16, .19, .25, 1),
            "chapel_front": (.18, .21, .28, 1),
            "chapel_lintel": (.19, .22, .29, 1),
            "chapel_roof": (.09, .12, .18, 1),
            "platform": (.13, .17, .21, 1),
            "step": (.19, .23, .27, 1),
            "parapet": (.17, .22, .27, 1),
            "altar": (.25, .17, .22, 1),
            "cover": (.18, .24, .27, 1),
            "buttress": (.14, .18, .25, 1),
        }
        for item in self.layout.blocks:
            color = palette.get(item.name, (.15, .18, .23, 1))
            box(self.solids, item.name, (item.x, item.y, item.z + item.h / 2),
                (item.w, item.d, item.h), color)
            if item.name in ("cover", "platform", "parapet", "buttress"):
                # Horizontal coping projects just 2 cm from its collider.
                box(self.solids, "stone-coping", (item.x, item.y, item.top - .055),
                    (item.w + .035, item.d + .035, .11), (.25, .30, .34, 1))
            if item.name == "step":
                box(self.neon, "stair-edge", (item.x, item.y - item.d / 2 - .006, item.top - .035),
                    (item.w - .25, .012, .037), (.15, .53, .62, 1))
            if item.name == "cover":
                box(self.shadows, "moon-cast-shadow",
                    (item.x + item.h * .26, item.y - item.h * .40, .013),
                    (item.w + item.h * .55, item.d + item.h * .83, .005),
                    (.004, .009, .02, .42))
                for xx in (-.32, .32):
                    box(self.solids, "cover-strap", (item.x + item.w * xx, item.y - item.d / 2 - .01,
                                                     item.h / 2), (.08, .035, item.h - .2), (.075, .11, .14, 1))
                box(self.neon, "cover-reflector", (item.x, item.y - item.d / 2 - .035, item.h - .26),
                    (.34, .016, .045), (.57, .36, .11, 1))

    def _pointed_window(self, x, y, bottom, width, height, color, heading=0):
        group = self.neon.attachNewNode("lancet-window")
        group.setPos(x, y, bottom)
        group.setH(heading)
        box(group, "illuminated-glass", (0, 0, height * .43),
            (width, .045, height * .76), color)
        # A pointed head and central mullion make a recognisable lancet.
        top = height * .8
        beam(group, (-width / 2, -.035, top), (0, -.035, height), .08, color)
        beam(group, (0, -.035, height), (width / 2, -.035, top), .08, color)
        box(group, "mullion", (0, -.034, height * .44), (.07, .03, height * .86), (.045, .065, .10, 1))
        for zz in (.27, .57):
            box(group, "glass-bar", (0, -.034, height * zz), (width, .03, .055), (.045, .065, .10, 1))

    def _chapel(self):
        # Deep pilasters and decorative pointed arches sit against solid walls.
        for x in (-9.6, -7.0, -3.2, 3.2, 7.0, 9.6):
            box(self.solids, "chapel-pilaster", (x, 14.95, 3.9), (.23, .13, 7.8), (.30, .32, .39, 1))
            cone(self.solids, "pilaster-pinnacle", (x, 15.2, 8.9), .42, 1.8, (.15, .20, .28, 1), 4)
        for x in (-8.2, -5.1, 5.1, 8.2):
            self._pointed_window(x, 14.94, 2.1, 1.0, 3.25, (.18, .43, .55, 1))
        box(self.solids, "chapel-string-course", (0, 14.94, 6.9), (20.8, .12, .16), (.32, .35, .43, 1))
        # The actual doorway clearance comes from layout's lintel at 5.7 m.
        for side in (-1, 1):
            beam(self.neon, (side * 2.91, 14.93, .25), (side * 2.91, 14.93, 5.9),
                 .06, (.18, .62, .75, 1))
            beam(self.neon, (side * 2.91, 14.93, 5.9), (0, 14.93, 7.35), .07, (.18, .62, .75, 1))
        self._sign("VESPER  /  IX", (0, 14.90, 7.3), .31, (.62, .76, .86, 1))
        # Red suspended reliquary: visual art installed above the altar.
        red = (.86, .16, .24, 1)
        for z, size in ((4.0, 1.22), (4.0, .78)):
            corners = [(0, 24.90, z + size), (size * .55, 24.90, z),
                       (0, 24.90, z - size), (-size * .55, 24.90, z)]
            for i in range(4):
                beam(self.neon, corners[i], corners[(i + 1) % 4], .07, red)
        beam(self.neon, (0, 24.86, 2.1), (0, 24.86, 5.9), .065, red)
        for x in (-8.5, 8.5):
            self._pointed_window(x, 24.94, 2.0, .7, 3.8, (.56, .10, .19, 1))
        for x in (-9.95, 9.95):
            for y in (18.0, 22.0):
                box(self.neon, "chapel-floor-light", (x, y, .25), (.035, .75, .1), (.70, .12, .21, 1))
        # Tiled aisle and water reflections extend into the shelter.
        box(self.solids, "chapel-aisle", (0, 20.4, .011), (4.1, 9.8, .015), (.13, .11, .15, 1))
        for x in (-1.96, 1.96):
            box(self.neon, "aisle-inlay", (x, 20.4, .024), (.025, 9.8, .018), (.38, .24, .21, 1))
        for y in (17.1, 18.7, 20.6, 22.4):
            box(self.water, "red-reflection", (0, y, .04), (.14 + (23 - y) * .06, .40, .01), (.59, .08, .12, .18))

    def _sign(self, label, pos, scale, color, heading=0):
        text = TextNode(label)
        text.setText(label)
        text.setAlign(TextNode.ACenter)
        text.setTextColor(*color)
        node = self.neon.attachNewNode(text)
        node.setPos(*pos)
        node.setScale(scale)
        node.setH(heading)
        node.setTwoSided(False)
        return node

    def _streets(self):
        for side in (-1, 1):
            # Pipes are flush with boundary wall faces.
            for z in (1.0, 4.5):
                beam(self.solids, (side * 25.86, -25, z), (side * 25.86, 25, z), .14,
                     (.16, .24, .28, 1))
            for y in (-17, -7.5, 3, 13):
                x = side * 25.8
                box(self.solids, "wall-lantern", (x, y, 3.4), (.2, .52, 1.0), (.055, .074, .09, 1))
                box(self.neon, "lantern-glow", (x - side * .115, y, 3.4), (.035, .34, .72), (.96, .52, .18, 1))
                box(self.water, "warm-rain-reflection", (side * 23.9, y, .035), (2.3, .23, .02), (.59, .30, .12, .25))
                pool = cylinder(self.haze, "lantern-light-pool", (side * 24.0, y, .018), 1,
                                .004, (.55, .32, .13, .09), sides=20)
                pool.setScale(1.8, 1.25, .004)
                if self.quality != "low":
                    # A low-opacity cone approximates scattering in wet air;
                    # its narrow apex points toward the wall-mounted lantern.
                    shaft = cone(self.haze, "lantern-light-shaft",
                                 (side * 24.83, y, 1.78), 1.45, 3.6,
                                 (.68, .40, .19, .017), sides=12)
                    shaft.setR(side * 28)
            self._sign("SECTOR  09", (side * 25.88, -12, 2.1), .35, (.37, .53, .63, 1), -90 * side)
        # Poster panels are surface decorations, not invisible obstacles.
        for x in (-20, 20):
            box(self.solids, "south-shutter", (x, -25.94, 2.2), (5.0, .05, 3.8), (.068, .095, .125, 1))
            for z in (.8, 1.2, 1.6, 2.0, 2.4, 2.8, 3.2, 3.6):
                box(self.solids, "shutter-slat", (x, -25.89, z), (4.8, .025, .055), (.19, .24, .28, 1))
        self._sign("NOCTURNE", (0, -25.89, 3.25), .77, (.14, .65, .82, 1), 180)
        self._sign("THE VEIL HAS BROKEN", (0, -25.87, 2.3), .25, (.58, .66, .73, 1), 180)
        # Hazard marks make changes in height easy to read during combat.
        for side in (-1, 1):
            for i in range(7):
                box(self.neon, "gallery-light", (side * 15.7 - 2.7 + i * .9, -3.508, 1.67),
                    (.36, .012, .055), (.62, .44, .16, 1))

    def _skyline(self):
        # A cathedral silhouette frames the north chapel without adding
        # inaccessible gameplay solids inside the collision boundary.
        roof_color = (.065, .090, .14, 1)
        stone = (.115, .145, .205, 1)
        for x in (-11.5, 11.5):
            box(self.solids, "cathedral-tower", (x, 32, 12), (6, 6, 24), stone)
            box(self.solids, "tower-cornice", (x, 32, 24), (6.5, 6.5, .55), (.22, .25, .31, 1))
            cone(self.solids, "cathedral-spire", (x, 32, 30.3), 4.4, 12.0, roof_color, 4)
            beam(self.neon, (x, 32, 35.8), (x, 32, 38.7), .045, (.19, .36, .47, 1))
            for level in (9, 15, 20):
                for dx in (-1.6, 0, 1.6):
                    self._pointed_window(x + dx, 28.97, level, .58, 2.9, (.19, .32, .41, 1))
            for dx in (-2.75, 2.75):
                box(self.solids, "tower-rib", (x + dx, 28.9, 12), (.2, .15, 24), (.22, .25, .31, 1))
        box(self.solids, "cathedral-nave", (0, 34, 8.8), (17, 10, 17.6), stone)
        pitched = box(self.solids, "cathedral-roof", (0, 34, 18), (11.8, 11.6, 11.8), roof_color)
        pitched.setR(45)
        self._pointed_window(0, 28.93, 10.2, 3.0, 6.5, (.33, .16, .30, 1))
        for side in (-1, 1):
            for i, y in enumerate(range(-30, 35, 9)):
                x = side * self.rng.uniform(31.0, 36.0)
                height = self.rng.uniform(12, 25)
                width, depth = self.rng.uniform(7.5, 10.0), self.rng.uniform(7, 9)
                value = self.rng.uniform(.8, 1.2)
                color = (.09 * value, .115 * value, .165 * value, 1)
                box(self.solids, "city-tenement", (x, y, height / 2), (width, depth, height), color)
                box(self.solids, "tenement-cornice", (x, y, height), (width + .25, depth + .3, .35), (.19, .22, .28, 1))
                if i % 2:
                    cone(self.solids, "city-roof", (x, y, height + 3.3), width * .72, 6.6, roof_color, 4)
                else:
                    box(self.solids, "roof-machinery", (x, y, height + 1), (width * .45, depth * .45, 2), roof_color)
                    cylinder(self.solids, "smokestack", (x + side * 2, y, height + 3), .5, 6, (.11, .14, .18, 1), 8)
                # Windows on the inward-facing wall, with irregular outages.
                for z in range(5, int(height - 1), 4):
                    for dy in (-2.0, 0, 2.0):
                        if self.rng.random() < .24:
                            continue
                        color = (.14, .25, .34, 1) if self.rng.random() < .72 else (.40, .28, .16, 1)
                        box(self.neon, "city-window", (x - side * (width / 2 + .015), y + dy, z),
                            (.03, .62, 1.35), color)
            # Rear blocks remain a soft distant silhouette.
            for x in range(-27, 28, 9):
                y = side * 36
                height = self.rng.uniform(10, 18)
                box(self.solids, "distant-city", (x, y, height / 2), (8, 7, height), (.085, .11, .16, 1))
        # Elevated utility cables across the skyline.
        for y in (-18, 7):
            last = (-29, y, 13)
            for i in range(1, 13):
                x = -29 + i * 58 / 12
                nxt = (x, y, 10.8 + 2.2 * (x / 29) ** 2)
                beam(self.solids, last, nxt, .035, (.018, .026, .039, 1))
                last = nxt

    def _moon(self):
        sky = self.root.attachNewNode("moon")
        sky.hide(self.shadow_mask)
        sky.setLightOff(1)
        sky.setFogOff(1)
        moon = cylinder(sky, "moon-disc", (-32, 65, 42), 4.6, .04, (.69, .81, .93, 1), 48)
        moon.setHpr(22, 114, 0)
        halo = cylinder(sky, "moon-halo", (-32, 65.15, 42), 6.7, .035, (.27, .43, .61, .09), 48)
        halo.setHpr(22, 114, 0)
        halo.setTransparency(TransparencyAttrib.MAlpha)
        halo.setDepthWrite(False)

    def _rain(self):
        count = {"low": 110, "medium": 230, "high": 400}.get(self.quality, 230)
        self.rain_seeds = [(self.rng.uniform(-18, 18), self.rng.uniform(-18, 18),
                            self.rng.uniform(0, 18), self.rng.uniform(.36, .85))
                           for _ in range(count)]
        self.rain_data = GeomVertexData("rain-vertices", GeomVertexFormat.getV3c4(), Geom.UHDynamic)
        self.rain_data.setNumRows(count * 2)
        colors = GeomVertexWriter(self.rain_data, "color")
        writer = GeomVertexWriter(self.rain_data, "vertex")
        lines = GeomLines(Geom.UHStatic)
        for i, (x, y, z, length) in enumerate(self.rain_seeds):
            writer.addData3(x, y, z)
            writer.addData3(x - .04, y, z + length)
            colors.addData4(.44, .63, .8, .13)
            colors.addData4(.44, .63, .8, .01)
            lines.addVertices(i * 2, i * 2 + 1)
        lines.closePrimitive()
        geometry = Geom(self.rain_data)
        geometry.addPrimitive(lines)
        node = GeomNode("rain-streaks")
        node.addGeom(geometry)
        self.rain = self.root.attachNewNode(node)
        self.rain.hide(self.shadow_mask)
        self.rain.setTransparency(TransparencyAttrib.MAlpha)
        self.rain.setDepthWrite(False)
        self.rain.setLightOff(1)
        self.rain.setRenderModeThickness(1)
        self._rain_tick = 0.0

    def update(self, dt, time, player_pos):
        self._rain_tick += dt
        # Rain updates at 30 Hz; the rest of the environment is batched static.
        if self._rain_tick < 1 / 30:
            return
        self._rain_tick = 0
        px, py = player_pos[0], player_pos[1]
        self.rain.setPos(px, py, 0)
        writer = GeomVertexWriter(self.rain_data, "vertex")
        for x, y, start_z, length in self.rain_seeds:
            z = (start_z - time * 16) % 18
            drift = (time * 1.3) % 36
            rx = (x + drift + 18) % 36 - 18
            # The chapel shelter protects the player from visible rain.
            under_roof = (-10.8 < px + rx < 10.8 and 14.7 < py + y < 26)
            if under_roof and z < 8.4:
                z += 18
            writer.setData3(rx, y, z)
            writer.setData3(rx - .065, y, z + length)
        self.rain.node().markBoundsStale()

    def destroy(self):
        for light in self.lights:
            self.base.render.clearLight(light)
        self.base.render.clearFog()
        if self.shader_shadows:
            self.base.render.clearShader()
        self.root.removeNode()

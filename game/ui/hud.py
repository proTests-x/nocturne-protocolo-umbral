"""Responsive, retained HUD; no GUI nodes are rebuilt during a frame."""
from pathlib import Path

from direct.gui.DirectGui import DirectButton, DirectFrame
from direct.gui import DirectGuiGlobals as DGG
from panda3d.core import Filename, LineSegs, TextNode, TransparencyAttrib


IVORY = (0.88, 0.92, 0.92, 1)
MUTED = (0.44, 0.55, 0.60, 1)
CYAN = (0.36, 0.92, 0.92, 1)
RED = (1.0, 0.25, 0.28, 1)
INK = (0.013, 0.027, 0.038, 0.86)


class HUD:
    """The app owns input/state; this class only renders it and calls buttons."""

    def __init__(self, base):
        self.base = base
        self.mode = "menu"
        self.state = {}
        self._text_values = {}
        self._aspect = 0
        self.font = None
        self.bold = None
        for attr, filename in (("font", "segoeui.ttf"), ("bold", "segoeuib.ttf")):
            path = Path("C:/Windows/Fonts") / filename
            if path.exists():
                try:
                    font = base.loader.loadFont(Filename.fromOsSpecific(str(path)).getFullpath())
                    font.setPixelsPerUnit(80)
                    setattr(self, attr, font)
                except Exception:
                    pass
        self.root = base.aspect2d.attachNewNode("interface")
        self.root.setDepthTest(False)
        self.root.setDepthWrite(False)
        self.root.setBin("fixed", 80)
        self.game = self.root.attachNewNode("game-hud")
        self.left = self.game.attachNewNode("left-anchor")
        self.right = self.game.attachNewNode("right-anchor")
        self._build_game()
        self.menu = self.root.attachNewNode("menu")
        self.menu_left = self.menu.attachNewNode("menu-left")
        self.menu_right = self.menu.attachNewNode("menu-right")
        self._build_menu()
        self.overlay = self.root.attachNewNode("overlay")
        self._build_overlay()
        self.resize()
        self.set_mode("menu")

    def _text(self, parent, name, value, x, z, size=.035, color=IVORY,
              align=TextNode.ALeft, bold=False):
        text = TextNode(name)
        text.setText(value)
        text.setTextColor(*color)
        text.setAlign(align)
        font = self.bold if bold else self.font
        if font:
            text.setFont(font)
        text.setShadow(.018, .024)
        text.setShadowColor(0, 0, 0, .5)
        node = parent.attachNewNode(text)
        node.setScale(size)
        node.setPos(x, 0, z)
        self._text_values[name] = value
        return node

    def _set(self, node, text):
        name = node.node().getName()
        value = str(text)
        if self._text_values.get(name) != value:
            node.node().setText(value)
            self._text_values[name] = value

    def _frame(self, parent, rect, color=INK):
        return DirectFrame(parent=parent, frameSize=rect, frameColor=color,
                           relief=DGG.FLAT, state="disabled")

    @staticmethod
    def _lines(parent, name, segments, color=CYAN, thickness=1.4):
        lines = LineSegs(name)
        lines.setThickness(thickness)
        lines.setColor(*color)
        for start, end in segments:
            lines.moveTo(start[0], 0, start[1])
            lines.drawTo(end[0], 0, end[1])
        node = parent.attachNewNode(lines.create())
        node.setTransparency(TransparencyAttrib.MAlpha)
        return node

    def _button(self, parent, text, z, command, primary=False):
        color = (.30, .85, .86, 1) if primary else (.045, .075, .095, .94)
        return DirectButton(
            parent=parent, text=text, text_font=self.bold or self.font,
            text_scale=.038, text_fg=(.025, .07, .075, 1) if primary else IVORY,
            text_align=TextNode.ALeft, text_pos=(.038, -.012),
            frameSize=(0, .67, -.058, .058),
            frameColor=(color, (.19, .5, .54, 1), (.40, .94, .94, 1), color),
            relief=DGG.FLAT, pos=(0, 0, z), command=command,
            pressEffect=False, rolloverSound=None, clickSound=None,
        )

    def _build_game(self):
        self.flash = self._frame(self.game, (-3, 3, -1, 1), (.75, .01, .04, 0))
        self.flash.setBin("fixed", 78)
        self._text(self.left, "hud-brand", "N / 09", 0, .91, .038, CYAN, bold=True)
        self._text(self.left, "hud-district", "DISTRITO VESPER", .165, .916, .027, MUTED)
        self.fps_text = self._text(self.left, "fps", "", 0, .86, .019, MUTED)
        self._text(self.right, "score-label", "PUNTUACIÓN", 0, .92, .027,
                   MUTED, TextNode.ARight)
        self.score = self._text(self.right, "score", "000000", 0, .845, .068,
                                IVORY, TextNode.ARight, True)
        self.combo = self._text(self.right, "combo", "", 0, .795, .026,
                                CYAN, TextNode.ARight)
        self._frame(self.game, (-.285, .285, .86, .99), (.012, .028, .042, .75))
        self.round = self._text(self.game, "round", "OLEADA 01", 0, .922, .036,
                                IVORY, TextNode.ACenter, True)
        self.remaining = self._text(self.game, "remaining", "", 0, .88, .027,
                                    CYAN, TextNode.ACenter)
        self._frame(self.left, (-.025, .405, -.90, -.70))
        self._text(self.left, "health-label", "INTEGRIDAD", 0, -.752, .027, MUTED)
        self.health = self._text(self.left, "health", "100", 0, -.84, .078,
                                 IVORY, bold=True)
        self._text(self.left, "health-max", "/ 100", .16, -.839, .028, MUTED)
        self._frame(self.left, (0, .35, -.88, -.866), (.12, .18, .20, 1))
        self.health_bar = self._frame(self.left, (0, .35, -.88, -.866), CYAN)
        self._text(self.left, "help", "ESC  pausa   ·   M  audio   ·   F3  FPS", 0,
                   -.955, .027, MUTED)
        self._frame(self.right, (-.40, .025, -.90, -.70))
        self.weapon = self._text(self.right, "weapon", "01 / PISTOLA", 0, -.752,
                                 .027, MUTED, TextNode.ARight, True)
        self.ammo = self._text(self.right, "ammo", "12", -.105, -.844, .09,
                               IVORY, TextNode.ARight, True)
        self.reserve = self._text(self.right, "reserve", "/ 096", 0, -.84,
                                  .03, MUTED, TextNode.ARight)
        self.reload = self._text(self.right, "reload", "R  RECARGAR", 0, -.887,
                                 .026, CYAN, TextNode.ARight)
        self._text(self.right, "weapon-help", "1  pistola   2  rifle   3  escopeta", 0,
                   -.955, .027, MUTED, TextNode.ARight)
        self.abilities = []
        for i, (key, label, names) in enumerate((
            ("Q", "DASH", ("dash", "dark_dash")),
            ("E", "PULSO", ("pulse", "onda", "energy_wave")),
            ("F", "VISIÓN", ("vision", "demon_vision")),
            ("X", "FURIA", ("fury", "furia")),
        )):
            x = (i - 1.5) * .19
            group = self.game.attachNewNode("ability-" + names[0])
            group.setX(x)
            self._frame(group, (-.077, .077, -.902, -.742), (.018, .035, .052, .88))
            self._text(group, "key-" + key, key, 0, -.793, .041, IVORY,
                       TextNode.ACenter, True)
            label_node = self._text(group, "ability-" + key, label, 0, -.836,
                                    .026, MUTED, TextNode.ACenter)
            cooldown = self._text(group, "cooldown-" + key, "LISTO", 0, -.879,
                                  .025, CYAN, TextNode.ACenter)
            bar = self._frame(group, (-.077, .077, -.906, -.900), CYAN)
            self.abilities.append((names, cooldown, bar, label_node))
        self.crosshair = self._lines(self.game, "crosshair", [
            ((-.018, 0), (-.007, 0)), ((.007, 0), (.018, 0)),
            ((0, -.018), (0, -.007)), ((0, .007), (0, .018)),
        ], (.83, .94, .95, .9), 1.4)
        self.dot = self._frame(self.game, (-.0011, .0011, -.0011, .0011), IVORY)
        self.hitmarker = self._lines(self.game, "hitmarker", [
            ((-.020, -.020), (-.01, -.01)), ((.010, .010), (.020, .020)),
            ((-.020, .020), (-.01, .01)), ((.010, -.010), (.020, -.020)),
        ], RED, 2.2)
        self.hitmarker.hide()
        self.toast = self._text(self.game, "toast", "", 0, .63, .043,
                                CYAN, TextNode.ACenter, True)

    def _build_menu(self):
        self.menu_scrim = self._frame(self.menu, (-3, 3, -1, 1), (.005, .015, .025, .39))
        self.menu_scrim.setBin("fixed", 79)
        self.menu_panel = self._frame(self.menu_left, (-.10, .93, -1, 1),
                                      (.009, .022, .034, .81))
        self._lines(self.menu_left, "menu-rule", [((0, .79), (.67, .79))],
                    (.22, .44, .49, .9), 1)
        self._text(self.menu_left, "menu-kicker", "N / 09     PROTOCOLO UMBRAL", 0, .847,
                   .031, CYAN, bold=True)
        self._text(self.menu_left, "menu-title", "NOCTURNE", -.006, .566, .150,
                   IVORY, bold=True)
        self._text(self.menu_left, "menu-title-small", "EL ÚLTIMO CAZADOR", .004, .483,
                   .038, MUTED)
        self._text(self.menu_left, "menu-desc", "La ciudad duerme. El abismo despierta.\n"
                   "Sobrevive a la noche. Rompe el umbral.", 0, .298, .034, IVORY)
        self._button(self.menu_left, "ENTRAR AL UMBRAL       →", .045,
                     self.base.start_game, True)
        self._button(self.menu_left, "SALIR", -.097, self.base.quit_game)
        self._text(self.menu_left, "menu-enter", "ENTER  para comenzar", 0, -.219,
                   .030, MUTED)
        self.menu_record = self._text(self.menu_left, "menu-record", "RÉCORD   000000", 0,
                                      -.384, .03, CYAN)
        self._lines(self.menu_left, "menu-bottom-rule", [((0, -.66), (.67, -.66))],
                    (.16, .31, .35, .9), 1)
        self._text(self.menu_left, "menu-foot", "FPS DE SUPERVIVENCIA\n"
                   "Oleadas infinitas / Arsenal y poderes", 0, -.732, .030, MUTED)
        self._text(self.menu_left, "menu-version", "PROTOTIPO JUGABLE    /    v1.0", 0,
                   -.916, .020, MUTED)

        self._text(self.menu_right, "sector-tag", "ZONA DE CONTENCIÓN", 0, .845, .026,
                   MUTED, TextNode.ARight)
        self._text(self.menu_right, "sector-name", "DISTRITO VESPER", 0, .78, .047,
                   IVORY, TextNode.ARight, True)
        self._text(self.menu_right, "sector-warning", "●  ACTIVIDAD SOBRENATURAL DETECTADA", 0,
                   .721, .024, RED, TextNode.ARight)
        self._frame(self.menu_right, (-.81, .04, -.907, -.175),
                    (.009, .022, .034, .82))
        self._text(self.menu_right, "controls-label", "MANUAL DEL CAZADOR", -.76, -.244,
                   .034, CYAN, bold=True)
        for i, (keys, action) in enumerate((
            ("W A S D", "Moverse"), ("MOUSE", "Mirar / disparar / apuntar"),
            ("SHIFT", "Correr"), ("ESPACIO", "Saltar"),
            ("CTRL / C", "Agacharse / deslizar"), ("R / 1 2 3", "Recargar / cambiar arma"),
            ("Q / E / F / X", "Dash / pulso / visión / furia"),
        )):
            z = -.331 - i * .071
            self._text(self.menu_right, "control-key-" + str(i), keys, -.76, z, .032,
                       IVORY, bold=True)
            self._text(self.menu_right, "control-action-" + str(i), action, -.43, z,
                       .032, MUTED)
        self._text(self.menu_right, "control-tip", "Muévete. Encadena bajas. Domina la noche.",
                   -.76, -.862, .027, CYAN)

    def _build_overlay(self):
        self.overlay_scrim = self._frame(self.overlay, (-3, 3, -1, 1), (.005, .012, .024, .88))
        self.overlay_scrim.setBin("fixed", 79)
        self._text(self.overlay, "overlay-kicker", "N / 09   ·   PROTOCOLO UMBRAL", 0, .59,
                   .028, CYAN, TextNode.ACenter, True)
        self.overlay_title = self._text(self.overlay, "overlay-title", "PAUSA", 0, .32,
                                        .12, IVORY, TextNode.ACenter, True)
        self.overlay_subtitle = self._text(self.overlay, "overlay-subtitle", "", 0, .205,
                                           .034, MUTED, TextNode.ACenter)
        self.overlay_stats = self._text(self.overlay, "overlay-stats", "", 0, .054,
                                        .045, IVORY, TextNode.ACenter, True)
        self.overlay_buttons = self.overlay.attachNewNode("overlay-buttons")
        self.overlay_buttons.setX(-.335)
        self.continue_button = self._button(self.overlay_buttons, "CONTINUAR      →", -.19,
                                            self._continue, True)
        self._button(self.overlay_buttons, "SALIR", -.333, self.base.quit_game)
        self._text(self.overlay, "overlay-footer", "LA NOCHE AÚN NO HA TERMINADO", 0,
                   -.64, .023, MUTED, TextNode.ACenter)

    def _continue(self):
        if self.mode == "paused":
            self.base.resume_game()
        else:
            self.base.start_game()

    def resize(self):
        aspect = self.base.getAspectRatio()
        if abs(aspect - self._aspect) < .001:
            return
        self._aspect = aspect
        margin = .09
        self.left.setX(-aspect + margin)
        self.right.setX(aspect - margin)
        # The menu stays usable down to 4:3; at narrow portrait ratios it scales.
        menu_scale = min(1.0, aspect / 1.27)
        self.menu_left.setScale(menu_scale)
        self.menu_right.setScale(menu_scale)
        self.menu_left.setX(-aspect + .11)
        self.menu_right.setX(aspect - .11)

    def set_mode(self, mode, state=None):
        self.mode = mode
        if state is not None:
            self.state = state
        self.game.show() if mode == "playing" else self.game.hide()
        self.menu.show() if mode == "menu" else self.menu.hide()
        self.overlay.show() if mode in ("paused", "dead") else self.overlay.hide()
        if mode in ("paused", "dead"):
            dead = mode == "dead"
            self._set(self.overlay_title, "CAZADOR CAÍDO" if dead else "PAUSA")
            self._set(self.overlay_subtitle, "El umbral reclama otra vida. Vuelve a intentarlo."
                      if dead else "Respira. La ciudad puede esperar un instante.")
            self.continue_button["text"] = "VOLVER AL UMBRAL    →" if dead else "CONTINUAR      →"
        self._update_stats(self.state)

    def _update_stats(self, state):
        score = int(state.get("score", 0))
        record = int(state.get("high_score", 0))
        self._set(self.menu_record, f"RÉCORD   {record:06d}")
        self._set(self.overlay_stats, f"{score:06d} PTS    /    OLEADA {int(state.get('round', 1)):02d}")

    def update(self, state, dt):
        self.state = state
        self.resize()
        if self.mode != "playing":
            self._update_stats(state)
            return
        health = max(0, min(100, float(state.get("health", 100))))
        self._set(self.health, f"{health:.0f}")
        self.health_bar.setSx(health / 100)
        health_color = RED if health < 30 else CYAN
        self.health_bar["frameColor"] = health_color
        self.health.node().setTextColor(*(RED if health < 30 else IVORY))
        self._set(self.score, f"{int(state.get('score', 0)):06d}")
        combo = state.get("combo", 1)
        self._set(self.combo, f"× {combo:g}  COMBO" if combo > 1 else "")
        wave = max(1, int(state.get("round", 1)))
        intermission = float(state.get("intermission", 0) or 0)
        self._set(self.round, f"OLEADA {wave:02d}")
        self._set(self.remaining, f"SIGUIENTE EN {intermission:.0f}s" if intermission > 0
                  else f"{int(state.get('remaining', 0)):02d} HOSTILES")
        weapon = str(state.get("weapon", "Pistola")).upper()
        self._set(self.weapon, weapon)
        ammo = int(state.get("ammo", 0))
        self._set(self.ammo, f"{ammo:02d}")
        self.ammo.node().setTextColor(*(RED if ammo == 0 else IVORY))
        self._set(self.reserve, f"/ {int(state.get('reserve', 0)):03d}")
        reloading = state.get("reloading", False)
        self._set(self.reload, "RECARGANDO..." if reloading else "R  RECARGAR")
        powers = state.get("powers", {})
        for names, text, bar, label in self.abilities:
            info = next((powers[name] for name in names if name in powers), {})
            cooldown = max(0, float(info.get("cooldown", 0)))
            active = info.get("active", False)
            self._set(text, "ACTIVO" if active else (f"{cooldown:.1f}s" if cooldown > 0 else "LISTO"))
            color = CYAN if active or cooldown <= 0 else MUTED
            text.node().setTextColor(*color)
            bar["frameColor"] = color
        ads = max(0, min(1, float(state.get("ads", 0))))
        self.crosshair.setScale(1 - ads * .55)
        self.crosshair.setColorScale(1, 1, 1, 1 - ads * .55)
        self.hitmarker.show() if state.get("hitmarker", 0) > 0 else self.hitmarker.hide()
        flash = max(0, min(1, float(state.get("damage_flash", 0))))
        self.flash["frameColor"] = (.73, .015, .035, flash * .35)
        toast = state.get("toast", "") if state.get("toast_time", 0) > 0 else ""
        self._set(self.toast, toast)
        if state.get("fps", 0):
            self._set(self.fps_text, f"{state['fps']:.0f} FPS")
        else:
            self._set(self.fps_text, "")

    def destroy(self):
        self.root.removeNode()

"""Small procedural sound bank with bounded polyphony and dynamic music.

Drop WAV files in ``game/assets/sounds/<name>.wav`` to replace any sound.
The original synthesized fallback is generated in ``sounds/generated``.
All sound generation uses Python's standard library; no external assets.
"""
from array import array
import math
from pathlib import Path
import random
import sys
import wave


SOUND_NAMES = (
    "pistol", "rifle", "shotgun", "reload", "step", "impact", "roar",
    "dash", "pulse", "vision", "fury", "kill", "wave", "hurt",
)
RATE = 22050
TAU = math.tau
DURATIONS = {"pistol": .23, "rifle": .14, "shotgun": .48, "reload": .76,
             "step": .17, "impact": .20, "roar": .86, "dash": .42,
             "pulse": .75, "vision": .95, "fury": 1.15, "kill": .24,
             "wave": 1.6, "hurt": .27, "ambient": 8.0, "combat": 8.0}
VOLUMES = {"pistol": .55, "rifle": .38, "shotgun": .67, "reload": .29,
           "step": .19, "impact": .24, "roar": .28, "dash": .40,
           "pulse": .53, "vision": .40, "fury": .47, "kill": .24,
           "wave": .40, "hurt": .48}


def _synthesize(name, path):
    """Create mono PCM; deterministic timbres make startup reproducible."""
    duration = DURATIONS[name]
    rng = random.Random("nocturne-v1-" + name)
    samples = array("h")
    low_noise = 0.0
    count = int(duration * RATE)
    for i in range(count):
        t = i / RATE
        p = t / duration
        noise = rng.uniform(-1, 1)
        low_noise += .09 * (noise - low_noise)
        value = 0.0
        if name in ("pistol", "rifle", "shotgun"):
            decay = {"pistol": 28, "rifle": 42, "shotgun": 15}[name]
            pitch = {"pistol": 105, "rifle": 138, "shotgun": 68}[name]
            transient = noise * math.exp(-t * decay * 1.6)
            body = math.sin(TAU * (pitch * t - 35 * t * t)) * math.exp(-t * decay)
            tail = low_noise * math.exp(-t * decay * .4)
            value = .62 * transient + .55 * body + tail * .3
        elif name == "reload":
            for onset, pitch, amp in ((.02, 970, .45), (.27, 640, .38), (.57, 1450, .65)):
                age = t - onset
                if age > 0:
                    value += amp * (noise * .7 + math.sin(TAU * pitch * age) * .3) * math.exp(-age * 65)
        elif name == "step":
            value = (low_noise * 1.6 + math.sin(TAU * 69 * t) * .23) * math.exp(-t * 30)
            value += noise * .10 * math.exp(-abs(t - .045) * 45)
        elif name == "impact":
            value = (noise * .6 + math.sin(TAU * 1740 * t) * .3 + math.sin(TAU * 2780 * t) * .15) * math.exp(-t * 35)
        elif name == "roar":
            pitch = 48 * t + 20 * t * t
            value = (math.sin(TAU * pitch + 3 * math.sin(TAU * 21 * t)) * .32
                     + low_noise * 1.3) * math.sin(math.pi * p) ** .7
        elif name == "dash":
            value = (noise * .2 + low_noise * 1.5 + math.sin(TAU * (240 * t - 190 * t * t)) * .18) * math.sin(math.pi * p) ** 2
        elif name == "pulse":
            value = (math.sin(TAU * (85 * t - 28 * t * t)) * .7 + low_noise * .7) * math.exp(-t * 5)
            value += math.sin(TAU * 427 * t) * math.exp(-t * 13) * .16
        elif name == "vision":
            value = (math.sin(TAU * (190 * t + 130 * t * t)) * .29
                     + math.sin(TAU * (285 * t + 195 * t * t)) * .12
                     + low_noise * .2) * math.sin(math.pi * p) ** 2
        elif name == "fury":
            value = (math.sin(TAU * (58 * t + 33 * t * t) + 2 * math.sin(TAU * 29 * t)) * .33
                     + low_noise * .8) * math.sin(math.pi * p)
        elif name == "kill":
            value = (math.sin(TAU * 660 * t) + .45 * math.sin(TAU * 990 * t)) * .35 * math.exp(-t * 25)
        elif name == "wave":
            value = (math.sin(TAU * 65.5 * t) * .35 + math.sin(TAU * 98.25 * t) * .15
                     + math.sin(TAU * 131 * t) * .14 + low_noise * .45) * math.sin(math.pi * p) ** 1.5
        elif name == "hurt":
            value = (low_noise * 1.2 + math.sin(TAU * (82 * t - 48 * t * t)) * .4) * math.exp(-t * 14)
        elif name == "ambient":
            # Integer cycles in eight seconds make the drone seamless.
            value = (math.sin(TAU * 49 * t) * .18 + math.sin(TAU * 73.5 * t) * .10
                     + math.sin(TAU * 98.125 * t) * .05)
            value *= .65 + .2 * math.sin(TAU * .125 * t)
            value += low_noise * .06 * math.sin(math.pi * p) ** 2
        elif name == "combat":
            beat = t % .5
            value = math.sin(TAU * (55 * beat - 25 * beat * beat)) * math.exp(-beat * 17) * .43
            value += noise * .14 * math.exp(-((t + .25) % .5) * 65)
            value += math.sin(TAU * 98 * t) * .045 * (1 + math.sin(TAU * 2 * t))
        # Very short ramps remove clicks while preserving sharp attack.
        if name not in ("ambient", "combat"):
            value *= min(1, t / .0015, (duration - t) / .008)
        samples.append(int(max(-.96, min(.96, value)) * 32767))
    if sys.byteorder != "little":
        samples.byteswap()
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(RATE)
        handle.writeframes(samples.tobytes())


class SoundSystem:
    """Only this class touches Panda audio; headless/no-device mode is safe."""

    def __init__(self, base, enabled=True):
        self.base = base
        self.muted = not enabled
        self.available = False
        self.voices = {}
        self.indices = {}
        self.ambient = None
        self.combat = None
        self.intensity = 0.0
        self.master_fade = 0.0
        self.directory = Path(__file__).resolve().parents[1] / "assets" / "sounds"
        try:
            from panda3d.core import Filename
            generated = self.directory / "generated"
            generated.mkdir(parents=True, exist_ok=True)
            for name in (*SOUND_NAMES, "ambient", "combat"):
                custom = self.directory / (name + ".wav")
                path = custom if custom.exists() else generated / (name + ".wav")
                if not path.exists():
                    _synthesize(name, path)
                filename = Filename.fromOsSpecific(str(path))
                if name in ("ambient", "combat"):
                    sound = base.loader.loadMusic(filename)
                    if sound:
                        sound.setLoop(True)
                        sound.setVolume(0)
                        sound.play()
                        setattr(self, name, sound)
                else:
                    # Instances are distinct so automatic rifle fire doesn't
                    # restart the previous shot. Four voices cap heavy sounds.
                    count = 4 if name in ("pistol", "rifle", "shotgun", "impact", "step") else 2
                    bank = [base.loader.loadSfx(filename) for _ in range(count)]
                    self.voices[name] = [voice for voice in bank if voice]
                    self.indices[name] = 0
            self.available = True
        except Exception as exc:
            # Gameplay remains fully usable if a device or write access fails.
            print("Audio desactivado:", exc)
            self.destroy()

    def play(self, name, volume=1.0):
        if self.muted or not self.available:
            return
        bank = self.voices.get(name)
        if not bank:
            return
        index = self.indices[name]
        self.indices[name] = (index + 1) % len(bank)
        voice = bank[index]
        voice.setVolume(max(0, min(1, VOLUMES.get(name, .35) * volume)))
        voice.play()

    def update(self, dt, in_combat=False):
        if not self.available:
            return
        dt = max(0.0, min(.1, dt))
        blend = 1 - math.exp(-dt * 1.6)
        self.intensity += ((1.0 if in_combat else 0.0) - self.intensity) * blend
        self.master_fade += ((0.0 if self.muted else 1.0) - self.master_fade) * min(1, dt * 3)
        if self.ambient:
            self.ambient.setVolume((.33 - .10 * self.intensity) * self.master_fade)
        if self.combat:
            self.combat.setVolume(.30 * self.intensity * self.master_fade)

    def set_muted(self, muted):
        self.muted = bool(muted)
        if self.muted:
            for bank in self.voices.values():
                for voice in bank:
                    voice.stop()
            for sound in (self.ambient, self.combat):
                if sound:
                    sound.setVolume(0)

    def destroy(self):
        self.available = False
        for bank in self.voices.values():
            for sound in bank:
                sound.stop()
        for sound in (self.ambient, self.combat):
            if sound:
                sound.stop()
        self.voices.clear()

"""Three weapons share a testable ammunition and timing model."""
from .pistol import PISTOL
from .rifle import RIFLE
from .shotgun import SHOTGUN
LOADOUT = (PISTOL, RIFLE, SHOTGUN)

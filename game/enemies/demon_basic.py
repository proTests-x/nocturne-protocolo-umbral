"""Standard pursuing demon factory."""
from .enemy import make_enemy


def create(identifier, position, wave=1):
    return make_enemy(identifier, "basic", position, wave)

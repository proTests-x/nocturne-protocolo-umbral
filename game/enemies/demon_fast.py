"""Fragile, fast pursuer factory."""
from .enemy import make_enemy


def create(identifier, position, wave=1):
    return make_enemy(identifier, "fast", position, wave)

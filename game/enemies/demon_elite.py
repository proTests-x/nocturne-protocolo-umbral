"""Strafing and charging elite factory."""
from .enemy import make_enemy


def create(identifier, position, wave=1):
    return make_enemy(identifier, "elite", position, wave)

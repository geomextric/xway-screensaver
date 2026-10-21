"""Animation registry.

To add an animation: create a module in this package with an Animation subclass
(see base.py), then add it to ALL. The settings window builds its controls from
the class's SETTINGS, so no GUI code is needed.
"""
from . import lightspeed, polyglow, ripples

ALL = (polyglow.Polyglow, lightspeed.Lightspeed, ripples.Ripples)
BY_NAME = {anim.NAME: anim for anim in ALL}

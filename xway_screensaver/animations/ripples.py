"""Ripples: neon rings spreading out from random points across the desktop."""
import colorsys
import math
import random

from .base import Animation, Setting, glow_settings


class Ripples(Animation):
    NAME = "ripples"
    LABEL = "Ripples"
    SETTINGS = (
        Setting("rate", "Ripples per second", 0.2, 10, 0.1, 1, 2.0, "Ripples"),
        Setting("speed", "Speed", 50, 1000, 10, 0, 220, "Ripples"),
        Setting("size", "Size", 100, 3000, 50, 0, 900, "Ripples"),
        Setting("rings", "Rings per ripple", 1, 6, 1, 0, 3, "Ripples"),
        Setting("ring_gap", "Ring spacing", 10, 200, 5, 0, 45, "Ripples"),
        *glow_settings(strength=1.2, size=0.8, core=2.0, whiteness=0.5),
        Setting("saturation", "Saturation", 0, 1, 0.05, 2, 0.9, "Colour"),
        Setting("hue_speed", "Colour cycle speed", 0, 0.5, 0.005, 3, 0.05, "Colour"),
    )

    def __init__(self, bounds, cfg):
        super().__init__(bounds, cfg)
        self.ripples = []   # [x, y, radius, hue]
        self.hue = random.random()
        self.owed = 0.0     # ripples the spawn rate owes us

    def step(self, dt):
        cfg = self.cfg
        x0, y0, x1, y1 = self.bounds
        self.hue = (self.hue + cfg["hue_speed"] * dt) % 1.0
        self.owed += cfg["rate"] * dt
        while self.owed >= 1:
            self.owed -= 1
            hue = (self.hue + random.uniform(-0.08, 0.08)) % 1.0
            self.ripples.append([random.uniform(x0, x1), random.uniform(y0, y1), 0.0, hue])
        grow = cfg["speed"] * dt
        for ripple in self.ripples:
            ripple[2] += grow
        self.ripples = [r for r in self.ripples if r[2] < cfg["size"]]

    def draw(self, cr, view, neon):
        cfg = self.cfg
        vx0, vy0, vx1, vy1 = view
        margin = neon.reach * 1.5  # the largest ring scale
        size, rings, gap, sat = cfg["size"], cfg["rings"], cfg["ring_gap"], cfg["saturation"]
        for x, y, radius, hue in self.ripples:
            rgb = colorsys.hsv_to_rgb(hue, sat, 1.0)
            for i in range(rings):
                r = radius - i * gap
                if r <= 0:
                    break
                if (x + r < vx0 - margin or x - r > vx1 + margin
                        or y + r < vy0 - margin or y - r > vy1 + margin):
                    continue
                age = r / size  # 0 when born, 1 when gone
                cr.new_sub_path()
                cr.arc(x, y, r, 0, 2 * math.pi)
                neon.stroke(rgb, (1 - age) ** 1.5, 1.5 - age)  # rings thin and fade as they spread

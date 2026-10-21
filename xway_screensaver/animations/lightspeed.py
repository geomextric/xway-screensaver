"""Lightspeed: neon stars streaking out from the middle of the desktop."""
import colorsys
import random

from .base import Animation, Setting, glow_settings


class Lightspeed(Animation):
    NAME = "lightspeed"
    LABEL = "Lightspeed"
    SETTINGS = (
        Setting("stars", "Stars", 50, 2000, 10, 0, 400, "Stars"),
        Setting("speed", "Speed", 0.1, 3, 0.05, 2, 0.6, "Stars"),
        Setting("streak", "Streak length", 0, 0.5, 0.01, 2, 0.1, "Stars"),
        *glow_settings(strength=1.0, size=0.5, core=1.2, whiteness=0.6),
        Setting("saturation", "Saturation", 0, 1, 0.05, 2, 0.8, "Colour"),
        Setting("hue_speed", "Colour cycle speed", 0, 0.5, 0.005, 3, 0.02, "Colour"),
    )

    def __init__(self, bounds, cfg):
        super().__init__(bounds, cfg)
        self.stars = []   # [x, y, z, hue]; x and y in -1..1 of the desktop at depth z = 1
        self.drawn = []   # (tail, head, scale, alpha, hue) for this frame
        self.hue_shift = 0.0

    @staticmethod
    def _star(z=None):
        return [random.uniform(-1, 1), random.uniform(-1, 1),
                random.uniform(0.05, 1) if z is None else z, random.random()]

    def step(self, dt):
        cfg = self.cfg
        count = cfg["stars"]
        del self.stars[count:]
        self.stars.extend(self._star() for _ in range(count - len(self.stars)))
        self.hue_shift = (self.hue_shift + cfg["hue_speed"] * dt) % 1.0

        x0, y0, x1, y1 = self.bounds
        cx, cy, hw, hh = (x0 + x1) / 2, (y0 + y1) / 2, (x1 - x0) / 2, (y1 - y0) / 2
        dz = cfg["speed"] * dt * 0.5
        self.drawn = []
        for i, star in enumerate(self.stars):
            star[2] -= dz
            x, y, z = star[0], star[1], star[2]
            if z <= 0.01 or abs(x / z) > 1.05 or abs(y / z) > 1.05:
                self.stars[i] = self._star(1.0)
                continue
            tz = min(z + cfg["streak"], 1.0)
            near = 1.0 - z
            self.drawn.append(((cx + x / tz * hw, cy + y / tz * hh), (cx + x / z * hw, cy + y / z * hh),
                               0.4 + 2.2 * near, min(1.0, near * 1.6), star[3]))

    def draw(self, cr, view, neon):
        vx0, vy0, vx1, vy1 = view
        margin = neon.reach * 2.6  # the largest star scale
        sat = self.cfg["saturation"]
        for (tx, ty), (hx, hy), scale, alpha, hue in self.drawn:
            if (max(tx, hx) < vx0 - margin or min(tx, hx) > vx1 + margin
                    or max(ty, hy) < vy0 - margin or min(ty, hy) > vy1 + margin):
                continue
            cr.move_to(tx, ty)
            cr.line_to(hx, hy)
            neon.stroke(colorsys.hsv_to_rgb((hue + self.hue_shift) % 1.0, sat, 1.0), alpha, scale)

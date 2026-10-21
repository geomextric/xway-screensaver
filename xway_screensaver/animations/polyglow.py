"""Polyglow: bouncing polygons with fading, colour-shifting neon trails."""
import colorsys
import math
import random
from collections import deque

from .base import Animation, Setting, glow_settings


def _speed_factor():
    return random.uniform(0.5, 1.0)


class _Shape:
    def __init__(self, anim, hue):
        x0, y0, x1, y1 = anim.bounds
        self.anim = anim
        self.hue = hue
        self.pts = [[random.uniform(x0, x1), random.uniform(y0, y1)]
                    for _ in range(anim.cfg["vertices"])]
        # Velocities as signed fractions of cfg["speed"], so speed changes apply live.
        self.vel = [[random.choice((-1, 1)) * _speed_factor(), random.choice((-1, 1)) * _speed_factor()]
                    for _ in self.pts]
        self.history = deque(maxlen=anim.cfg["trail"])  # (points, hue), newest last
        self.since_echo = 0.0

    def step(self, dt):
        cfg = self.anim.cfg
        x0, y0, x1, y1 = self.anim.bounds
        for p, v in zip(self.pts, self.vel):
            for axis, lo, hi in ((0, x0, x1), (1, y0, y1)):
                p[axis] += v[axis] * cfg["speed"] * dt
                if p[axis] < lo or p[axis] > hi:
                    p[axis] = min(max(p[axis], lo), hi)
                    v[axis] = -math.copysign(_speed_factor(), v[axis])
        self.hue = (self.hue + cfg["hue_speed"] * dt) % 1.0
        if self.history.maxlen != cfg["trail"]:
            self.history = deque(self.history, maxlen=cfg["trail"])
        self.since_echo += dt
        if self.since_echo >= cfg["trail_gap"]:
            self.since_echo = 0.0
            self.history.append(([tuple(p) for p in self.pts], self.hue))


class Polyglow(Animation):
    NAME = "polyglow"
    LABEL = "Polyglow"
    SETTINGS = (
        Setting("shapes", "Shapes", 1, 6, 1, 0, 2, "Shapes"),
        Setting("vertices", "Corners", 3, 8, 1, 0, 4, "Shapes"),
        Setting("speed", "Speed", 100, 1500, 10, 0, 520, "Shapes"),
        Setting("trail", "Trail length", 1, 30, 1, 0, 8, "Shapes"),
        Setting("trail_gap", "Trail spacing", 0.01, 0.2, 0.005, 3, 0.045, "Shapes"),
        *glow_settings(),
        Setting("hue_speed", "Colour cycle speed", 0, 0.5, 0.005, 3, 0.04, "Colour"),
        Setting("saturation", "Saturation", 0, 1, 0.05, 2, 1.0, "Colour"),
    )

    def __init__(self, bounds, cfg):
        super().__init__(bounds, cfg)
        self._build()

    def _build(self):
        self.layout = (self.cfg["shapes"], self.cfg["vertices"])
        n = self.cfg["shapes"]
        self.shapes = [_Shape(self, i / n) for i in range(n)]

    def step(self, dt):
        if self.layout != (self.cfg["shapes"], self.cfg["vertices"]):
            self._build()
        for shape in self.shapes:
            shape.step(dt)

    def draw(self, cr, view, neon):
        vx0, vy0, vx1, vy1 = view
        margin = neon.reach
        for shape in self.shapes:
            n = len(shape.history)
            for age, (pts, hue) in enumerate(shape.history):
                xs, ys = [p[0] for p in pts], [p[1] for p in pts]
                if (max(xs) < vx0 - margin or min(xs) > vx1 + margin
                        or max(ys) < vy0 - margin or min(ys) > vy1 + margin):
                    continue
                cr.move_to(*pts[0])
                for p in pts[1:]:
                    cr.line_to(*p)
                cr.close_path()
                neon.stroke(colorsys.hsv_to_rgb(hue, self.cfg["saturation"], 1.0), (age + 1) / n)

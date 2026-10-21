"""Base class and shared neon drawing for animations.

No GTK imports here: the screensaver uses GTK3 (layer-shell) and the settings
window GTK4, and both hand animations a plain cairo context.
"""
from typing import NamedTuple

import cairo


class Setting(NamedTuple):
    key: str
    label: str
    lo: float
    hi: float
    step: float
    digits: int       # 0 means an integer setting
    default: float
    group: str


class Animation:
    """One animation, simulated in global (logical) coordinates.

    bounds is (x0, y0, x1, y1) across all monitors; the screensaver draws each
    monitor's slice, so anything that crosses a monitor border just carries on.
    cfg is this animation's own settings dict and may change while running.
    """

    NAME = ""
    LABEL = ""
    SETTINGS = ()

    @classmethod
    def defaults(cls):
        return {s.key: s.default for s in cls.SETTINGS}

    def __init__(self, bounds, cfg):
        self.bounds = bounds
        self.cfg = cfg

    def step(self, dt):
        """Advance by dt seconds."""

    def draw(self, cr, view, neon):
        """Draw onto cr, which is black and in global coordinates.

        view is the (x0, y0, x1, y1) area being drawn, for skipping offscreen work.
        neon.stroke() strokes cr's current path as a glowing line.
        """


def render(anim, cr, view):
    """Draw anim's view area onto cr (black, in global coordinates)."""
    cr.save()
    anim.draw(cr, view, Neon(cr, anim.cfg))
    cr.restore()


GLOW = ((18, 0.04), (10, 0.08), (5, 0.18))  # (width, alpha) halo passes at strength/size 1


def glow_settings(strength=1.0, size=1.0, core=1.6, whiteness=0.55):
    return (
        Setting("glow_strength", "Glow strength", 0, 3, 0.05, 2, strength, "Glow"),
        Setting("glow_size", "Glow size", 0, 3, 0.05, 2, size, "Glow"),
        Setting("core_width", "Core thickness", 0.5, 6, 0.1, 1, core, "Glow"),
        Setting("core_whiteness", "Core whiteness", 0, 1, 0.05, 2, whiteness, "Glow"),
    )


class Neon:
    """Strokes paths as neon tubes: soft halo passes under a bright core."""

    def __init__(self, cr, cfg):
        self.cr = cr
        self.glow = [(w * cfg["glow_size"], min(a * cfg["glow_strength"], 1.0)) for w, a in GLOW]
        self.glow = [(w, a) for w, a in self.glow if w > 0 and a > 0]
        self.core_width = cfg["core_width"]
        self.whiteness = cfg["core_whiteness"]
        # How far a stroke reaches past its path at scale 1, for culling offscreen work.
        self.reach = max([self.core_width] + [w for w, _ in self.glow]) / 2 + 1
        cr.set_line_join(cairo.LINE_JOIN_ROUND)
        cr.set_line_cap(cairo.LINE_CAP_ROUND)
        cr.set_operator(cairo.OPERATOR_ADD)  # overlapping light brightens

    def stroke(self, rgb, alpha=1.0, scale=1.0):
        """Stroke and clear cr's current path."""
        cr, (r, g, b), w = self.cr, rgb, self.whiteness
        for width, glow_alpha in self.glow:
            cr.set_line_width(width * scale)
            cr.set_source_rgba(r, g, b, glow_alpha * alpha)
            cr.stroke_preserve()
        cr.set_line_width(self.core_width * scale)
        cr.set_source_rgba(r + (1 - r) * w, g + (1 - g) * w, b + (1 - b) * w, alpha)
        cr.stroke()

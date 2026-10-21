"""Parallel frame rendering.

Each monitor is split into horizontal strips, and every strip is drawn into its
own buffer on a thread pool. pycairo releases the GIL while cairo rasterises,
so the strips draw on separate CPU cores; the monitor windows then just copy
the finished buffers to the screen.
"""
import os
from concurrent.futures import ThreadPoolExecutor

import cairo

from .animations.base import render

MAX_STRIPS = 8  # per monitor


class Strip:
    def __init__(self, x, y, w, h, scale):
        self.rect = (x, y, w, h)
        self.surface = cairo.ImageSurface(cairo.FORMAT_RGB24, w * scale, h * scale)
        self.surface.set_device_scale(scale, scale)  # HiDPI: draw in logical units

    def render(self, anim):
        x, y, w, h = self.rect
        cr = cairo.Context(self.surface)
        cr.set_source_rgb(0, 0, 0)
        cr.paint()
        cr.translate(-x, -y)
        render(anim, cr, (x, y, x + w, y + h))

    def paint(self, cr, origin_x, origin_y):
        cr.set_source_surface(self.surface, self.rect[0] - origin_x, self.rect[1] - origin_y)
        cr.paint()


class Renderer:
    """monitors: [(x, y, width, height, scale)] in global logical coordinates."""

    def __init__(self, monitors):
        cores = os.cpu_count() or 1
        rows = max(1, min(MAX_STRIPS, cores // len(monitors)))
        self.monitors = []
        for x, y, w, h, scale in monitors:
            edges = [y + h * i // rows for i in range(rows + 1)]
            self.monitors.append([Strip(x, top, w, bottom - top, scale)
                                  for top, bottom in zip(edges, edges[1:])])
        self.strips = [strip for strips in self.monitors for strip in strips]
        self.pool = ThreadPoolExecutor(max_workers=min(cores, len(self.strips)))

    def render(self, anim):
        """Draw the next frame of anim into every strip; blocks until done."""
        for _ in self.pool.map(lambda strip: strip.render(anim), self.strips):
            pass

    def paint(self, index, cr, origin_x, origin_y):
        """Copy monitor index's finished strips onto its window's cr."""
        for strip in self.monitors[index]:
            strip.paint(cr, origin_x, origin_y)

"""The screensaver itself: a layer-shell overlay on every monitor (GTK3).

One animation runs in global (logical) coordinates; each monitor's overlay
draws its own slice, so the animation carries on across monitor borders.
Exits on any key, click, scroll or real mouse movement, and on SIGTERM/SIGINT.
"""
import fcntl
import math
import os
import random
import signal
import sys
import time

os.environ.setdefault("GDK_BACKEND", "wayland")

import gi

gi.require_version("Gdk", "3.0")
gi.require_version("Gtk", "3.0")
gi.require_version("GtkLayerShell", "0.1")
gi.require_foreign("cairo")  # needs python3-gi-cairo
from gi.repository import Gdk, GLib, Gtk, GtkLayerShell  # noqa: E402

from . import animations, cli, config  # noqa: E402
from .renderer import Renderer  # noqa: E402

GRACE = 1.0           # seconds to ignore input after start
MOVE_THRESHOLD = 12   # px of pointer travel that dismisses


class Screensaver:
    def __init__(self, anim_cls, anim_cfg):
        display = Gdk.Display.get_default()
        monitors = [display.get_monitor(i) for i in range(display.get_n_monitors())]
        if not monitors:
            sys.exit("xway-screensaver: no monitors")
        geoms = [m.get_geometry() for m in monitors]
        bounds = (min(g.x for g in geoms), min(g.y for g in geoms),
                  max(g.x + g.width for g in geoms), max(g.y + g.height for g in geoms))
        self.anim = anim_cls(bounds, anim_cfg)
        self.renderer = Renderer([(g.x, g.y, g.width, g.height, m.get_scale_factor())
                                  for g, m in zip(geoms, monitors)])
        self.start = time.monotonic()
        self.last_frame = None
        self.pointer_origin = None
        self.windows = [self._make_window(i, m) for i, m in enumerate(monitors)]
        # Drive the animation from a frame clock, not a timer. A timer outranks
        # GTK's redraw in the main loop, so if a frame takes longer than the
        # timer interval the timer is always due and the screen never repaints.
        self.windows[0].get_child().add_tick_callback(self._tick)

    def _make_window(self, index, monitor):
        win = Gtk.Window()
        GtkLayerShell.init_for_window(win)
        GtkLayerShell.set_namespace(win, "xway-screensaver")
        GtkLayerShell.set_layer(win, GtkLayerShell.Layer.OVERLAY)
        GtkLayerShell.set_monitor(win, monitor)
        for edge in (GtkLayerShell.Edge.TOP, GtkLayerShell.Edge.BOTTOM,
                     GtkLayerShell.Edge.LEFT, GtkLayerShell.Edge.RIGHT):
            GtkLayerShell.set_anchor(win, edge, True)
        GtkLayerShell.set_exclusive_zone(win, -1)  # cover panels and docks too
        GtkLayerShell.set_keyboard_mode(win, GtkLayerShell.KeyboardMode.EXCLUSIVE)

        area = Gtk.DrawingArea()
        area.connect("draw", self._draw, index, monitor.get_geometry())
        win.add(area)
        win.add_events(Gdk.EventMask.KEY_PRESS_MASK | Gdk.EventMask.BUTTON_PRESS_MASK
                       | Gdk.EventMask.POINTER_MOTION_MASK | Gdk.EventMask.SCROLL_MASK)
        win.connect("key-press-event", self._dismiss)
        win.connect("button-press-event", self._dismiss)
        win.connect("scroll-event", self._dismiss)
        win.connect("motion-notify-event", self._motion)
        win.connect("realize", self._hide_cursor)
        win.show_all()
        return win

    @staticmethod
    def _hide_cursor(win):
        cursor = Gdk.Cursor.new_for_display(win.get_display(), Gdk.CursorType.BLANK_CURSOR)
        win.get_window().set_cursor(cursor)

    def _armed(self):
        return time.monotonic() - self.start > GRACE

    def _dismiss(self, *_):
        if self._armed():
            Gtk.main_quit()
        return True

    def _motion(self, _win, event):
        x, y = event.x_root, event.y_root
        if self.pointer_origin is None or not self._armed():
            self.pointer_origin = (x, y)
        elif math.hypot(x - self.pointer_origin[0], y - self.pointer_origin[1]) > MOVE_THRESHOLD:
            Gtk.main_quit()
        return True

    def _tick(self, _area, clock):
        now = clock.get_frame_time() / 1e6
        if self.last_frame is not None:
            self.anim.step(min(now - self.last_frame, 0.1))
        self.last_frame = now
        self.renderer.render(self.anim)
        for win in self.windows:
            win.queue_draw()
        return GLib.SOURCE_CONTINUE

    def _draw(self, _area, cr, index, geom):
        self.renderer.paint(index, cr, geom.x, geom.y)
        return True


def single_instance():
    """Hold a lock for the life of the process and record our pid for `stop`."""
    lock = open(cli.pid_path(), "a+")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        sys.exit(0)  # already running
    lock.seek(0)
    lock.truncate()
    lock.write(str(os.getpid()))
    lock.flush()
    return lock


def run(name=None):
    _lock = single_instance()
    if not GtkLayerShell.is_supported():
        sys.exit("xway-screensaver: this compositor has no wlr-layer-shell support")
    cfg = config.load()
    if name is None:
        name = random.choice(list(animations.BY_NAME)) if cfg["random"] else cfg["animation"]
    Screensaver(animations.BY_NAME[name], cfg["animations"][name])
    for sig in (signal.SIGTERM, signal.SIGINT):
        GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, sig, Gtk.main_quit)
    Gtk.main()
    return 0

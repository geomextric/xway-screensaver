"""Settings window with a live preview (GTK4)."""
import os
import subprocess
import sys

import gi

gi.require_version("Gtk", "4.0")
gi.require_foreign("cairo")  # needs python3-gi-cairo
from gi.repository import GLib, Gtk  # noqa: E402

from . import APP_ID, animations, config  # noqa: E402
from .animations.base import render  # noqa: E402

SERVICE = "xway-screensaver.service"
PREVIEW_BOUNDS = (0, 0, 2560, 1440)  # the preview is one 1440p monitor in miniature


def systemctl(*args):
    result = subprocess.run(["systemctl", "--user", *args], capture_output=True, text=True)
    return result.returncode, (result.stdout + result.stderr).strip()


def heading(title):
    label = Gtk.Label(xalign=0, margin_top=8)
    label.set_markup(f"<b>{GLib.markup_escape_text(title)}</b>")
    return label


def grid():
    return Gtk.Grid(column_spacing=18, row_spacing=6)


class Blocked:
    """Block a signal handler for the duration of a with-block."""

    def __init__(self, obj, handler):
        self.obj, self.handler = obj, handler

    def __enter__(self):
        self.obj.handler_block(self.handler)

    def __exit__(self, *_):
        self.obj.handler_unblock(self.handler)


class SettingsWindow(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="xway-screensaver")
        self.set_default_size(580, 900)
        self.cfg = config.load()
        self.anim = None
        self.last_frame = None
        self.save_source = 0
        self.restart_source = 0
        self.scales = {}

        header = Gtk.HeaderBar()
        preview = Gtk.Button(label="Preview on all screens")
        preview.add_css_class("suggested-action")
        preview.connect("clicked", self.on_preview)
        header.pack_end(preview)
        reset = Gtk.Button(label="Reset")
        reset.set_tooltip_text("Restore this animation's default settings")
        reset.connect("clicked", self.on_reset)
        header.pack_start(reset)
        self.set_titlebar(header)

        area = Gtk.DrawingArea()
        area.set_content_height(280)
        area.set_draw_func(self.draw_preview)
        area.add_tick_callback(self.on_tick)
        frame = Gtk.Frame(child=area, margin_top=18, margin_start=18, margin_end=18)

        body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8,
                       margin_top=10, margin_bottom=18, margin_start=18, margin_end=18)
        choose = grid()
        self.dropdown = Gtk.DropDown.new_from_strings([a.LABEL for a in animations.ALL])
        self.dropdown.set_selected(list(animations.BY_NAME).index(self.cfg["animation"]))
        self.dropdown.set_hexpand(True)
        self.dropdown.connect("notify::selected", self.on_animation)
        shuffle = Gtk.Switch(halign=Gtk.Align.START, active=self.cfg["random"])
        shuffle.connect("notify::active", self.on_random)
        choose.attach(Gtk.Label(label="Animation", xalign=0), 0, 0, 1, 1)
        choose.attach(self.dropdown, 1, 0, 1, 1)
        choose.attach(Gtk.Label(label="Random each time", xalign=0), 0, 1, 1, 1)
        choose.attach(shuffle, 1, 1, 1, 1)
        body.append(choose)

        self.anim_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        body.append(self.anim_box)

        body.append(heading("Screensaver"))
        idle = grid()
        self.idle_switch = Gtk.Switch(halign=Gtk.Align.START)
        self.idle_switch.set_active(systemctl("is-enabled", SERVICE)[1] == "enabled")
        self.idle_handler = self.idle_switch.connect("notify::active", self.on_idle_toggled)
        minutes = Gtk.SpinButton.new_with_range(1, 120, 1)
        minutes.set_halign(Gtk.Align.START)
        minutes.set_value(self.cfg["idle_minutes"])
        minutes.connect("value-changed", self.on_minutes)
        idle.attach(Gtk.Label(label="Start when idle", xalign=0), 0, 0, 1, 1)
        idle.attach(self.idle_switch, 1, 0, 1, 1)
        idle.attach(Gtk.Label(label="After (minutes)", xalign=0), 0, 1, 1, 1)
        idle.attach(minutes, 1, 1, 1, 1)
        body.append(idle)

        scroller = Gtk.ScrolledWindow(child=body, vexpand=True)
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        outer.append(frame)
        outer.append(scroller)
        self.set_child(outer)
        self.show_animation()

    # Animation choice and its settings

    @property
    def anim_cls(self):
        return animations.ALL[self.dropdown.get_selected()]

    @property
    def anim_cfg(self):
        return self.cfg["animations"][self.anim_cls.NAME]

    def show_animation(self):
        self.anim = self.anim_cls(PREVIEW_BOUNDS, self.anim_cfg)
        while child := self.anim_box.get_first_child():
            self.anim_box.remove(child)
        self.scales = {}
        group, rows = None, None
        for s in self.anim_cls.SETTINGS:
            if s.group != group:
                group, rows = s.group, grid()
                self.anim_box.append(heading(group))
                self.anim_box.append(rows)
            scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, s.lo, s.hi, s.step)
            scale.set_digits(s.digits)
            scale.set_draw_value(True)
            scale.set_value_pos(Gtk.PositionType.RIGHT)
            scale.set_hexpand(True)
            scale.set_value(self.anim_cfg[s.key])
            scale.connect("value-changed", self.on_scale, s)
            row = len(self.scales)
            rows.attach(Gtk.Label(label=s.label, xalign=0), 0, row, 1, 1)
            rows.attach(scale, 1, row, 1, 1)
            self.scales[s.key] = scale

    def on_animation(self, _dropdown, _pspec):
        self.cfg["animation"] = self.anim_cls.NAME
        self.queue_save()
        self.show_animation()

    def on_random(self, switch, _pspec):
        self.cfg["random"] = switch.get_active()
        self.queue_save()

    def on_scale(self, scale, setting):
        value = scale.get_value()
        self.anim_cfg[setting.key] = int(round(value)) if setting.digits == 0 else round(value, setting.digits)
        self.queue_save()

    def on_reset(self, _button):
        for s in self.anim_cls.SETTINGS:
            self.scales[s.key].set_value(s.default)

    # Preview

    def on_tick(self, area, clock):
        now = clock.get_frame_time() / 1e6
        if self.last_frame is not None:
            self.anim.step(min(now - self.last_frame, 0.1))
        self.last_frame = now
        area.queue_draw()
        return GLib.SOURCE_CONTINUE

    def draw_preview(self, _area, cr, width, height):
        cr.set_source_rgb(0, 0, 0)
        cr.paint()
        x0, y0, x1, y1 = PREVIEW_BOUNDS
        scale = min(width / (x1 - x0), height / (y1 - y0))
        cr.translate((width - (x1 - x0) * scale) / 2, (height - (y1 - y0) * scale) / 2)
        cr.scale(scale, scale)
        cr.rectangle(x0, y0, x1 - x0, y1 - y0)
        cr.clip()
        render(self.anim, cr, PREVIEW_BOUNDS)

    def on_preview(self, _button):
        self.flush()
        subprocess.Popen([os.path.abspath(sys.argv[0]), "run", self.anim_cls.NAME])

    # Saving

    def queue_save(self):
        if self.save_source:
            GLib.source_remove(self.save_source)
        self.save_source = GLib.timeout_add(400, self.save)

    def save(self):
        self.save_source = 0
        config.save(self.cfg)
        return GLib.SOURCE_REMOVE

    def flush(self):
        """Save now, cancelling any pending delayed save."""
        if self.save_source:
            GLib.source_remove(self.save_source)
        self.save()

    # Idle service

    def on_idle_toggled(self, switch, _pspec):
        action = "enable" if switch.get_active() else "disable"
        code, output = systemctl(action, "--now", SERVICE)
        if code:
            with Blocked(switch, self.idle_handler):
                switch.set_active(not switch.get_active())
            self.error("Couldn't change the idle service", output)

    def on_minutes(self, spin):
        self.cfg["idle_minutes"] = spin.get_value_as_int()
        self.flush()
        if self.restart_source:
            GLib.source_remove(self.restart_source)
        self.restart_source = GLib.timeout_add(800, self.restart_idle)

    def restart_idle(self):
        self.restart_source = 0
        systemctl("try-restart", SERVICE)  # picks up the new timeout if it is running
        return GLib.SOURCE_REMOVE

    def error(self, message, detail):
        Gtk.AlertDialog(message=message, detail=detail).show(self)


class App(Gtk.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID)

    def do_activate(self):
        Gtk.Settings.get_default().set_property("gtk-application-prefer-dark-theme", True)
        Gtk.Window.set_default_icon_name(APP_ID)
        (self.props.active_window or SettingsWindow(self)).present()

    def do_shutdown(self):
        window = self.props.active_window
        if window:
            window.flush()
        Gtk.Application.do_shutdown(self)


def run():
    return App().run([sys.argv[0]])

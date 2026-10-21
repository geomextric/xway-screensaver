<img src="data/io.github.geomextric.XwayScreensaver.svg" width="96" align="right" alt="">

# xway-screensaver

Neon screensaver animations for Wayland desktops. One animation runs as a
single scene across every monitor, so shapes and stars travel from screen to
screen.

Animations:

- **Polyglow**: bouncing polygons with fading, colour-shifting neon trails
- **Lightspeed**: stars streaking out from the middle of your desktop

A settings window lets you pick the animation (or a random one each time),
tune it with a live preview, and choose how long until it starts.

## Does it work on my desktop?

It's a native Wayland app, not an X11 one. Your compositor needs two Wayland
protocols: **wlr-layer-shell** (to cover the screens) and **ext-idle-notify**
(to know when you're away).

| Desktop | Works |
|---|---|
| COSMIC (Pop!_OS 24.04) | Yes, tested |
| KDE Plasma 6, Sway, Hyprland, niri, labwc | Should work (not tested yet) |
| GNOME | No: GNOME supports neither protocol |

It does **not** lock the screen. Keep your desktop's own lock screen for
that; it draws on top of the screensaver.

## Install

### Ubuntu, Pop!_OS, Debian

Download the `.deb` from [Releases](https://github.com/geomextric/xway-screensaver/releases)
and install it; apt pulls in everything it needs:

```sh
sudo apt install ./xway-screensaver_*_all.deb
```

### From source (any distro)

Install the dependencies:

```sh
# Debian / Ubuntu / Pop!_OS
sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-3.0 gir1.2-gtk-4.0 gir1.2-gtklayershell-0.1 swayidle
# Arch
sudo pacman -S python-gobject python-cairo gtk3 gtk4 gtk-layer-shell swayidle
# Fedora
sudo dnf install python3-gobject python3-cairo gtk3 gtk4 gtk-layer-shell swayidle
```

Then install for your user (into `~/.local`):

```sh
git clone https://github.com/geomextric/xway-screensaver.git
cd xway-screensaver
./install.sh
```

`./uninstall.sh` removes it again.

## Use

Open **xway-screensaver** from your app menu and turn on **Start when idle**.
Any key, click or mouse movement closes the screensaver.

From a terminal:

```sh
xway-screensaver                 # show it now
xway-screensaver run lightspeed  # show a particular animation
xway-screensaver list            # list the animations
xway-screensaver settings        # open the settings window
```

Settings live in `~/.config/xway-screensaver/config.json`.

## Adding an animation

Each animation is one file in `xway_screensaver/animations/`: a subclass of
`Animation` (see `base.py`) with a `step(dt)` and a `draw(cr, view, neon)`
that draws with cairo in desktop coordinates (`neon.stroke()` gives a path the
glow). Its `SETTINGS` list becomes sliders
in the settings window automatically. Add the class to `ALL` in
`animations/__init__.py`, then try it with
`./bin/xway-screensaver run <name>`.

## Licence

MIT

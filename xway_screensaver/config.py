"""Settings file: ~/.config/xway-screensaver/config.json."""
import json
import os

from . import animations

PATH = os.path.join(os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config")),
                    "xway-screensaver", "config.json")

GENERAL = {
    "animation": animations.ALL[0].NAME,
    "random": False,      # pick a random animation each time instead
    "idle_minutes": 5,
}


def defaults():
    return {**GENERAL, "animations": {a.NAME: a.defaults() for a in animations.ALL}}


def _merge(target, saved):
    for key, value in saved.items():
        if key in target and not isinstance(target[key], dict):
            try:
                target[key] = type(target[key])(value)
            except (TypeError, ValueError):
                pass


def load():
    cfg = defaults()
    try:
        with open(PATH) as f:
            saved = json.load(f)
    except (OSError, ValueError):
        return cfg
    if not isinstance(saved, dict):
        return cfg
    _merge(cfg, saved)
    if cfg["animation"] not in animations.BY_NAME:
        cfg["animation"] = GENERAL["animation"]
    for name, values in (saved.get("animations") or {}).items():
        if name in cfg["animations"] and isinstance(values, dict):
            _merge(cfg["animations"][name], values)
    return cfg


def save(cfg):
    os.makedirs(os.path.dirname(PATH), exist_ok=True)
    tmp = PATH + ".tmp"
    with open(tmp, "w") as f:
        json.dump(cfg, f, indent=2)
    os.replace(tmp, PATH)

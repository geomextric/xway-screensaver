"""Command line: xway-screensaver [run|stop|idle|settings|list]."""
import argparse
import fcntl
import os
import shlex
import shutil
import signal
import sys

from . import __version__, animations, config


def pid_path():
    return os.path.join(os.environ.get("XDG_RUNTIME_DIR", "/tmp"), "xway-screensaver.pid")


def cmd_run(args):
    from . import screensaver  # GTK3: imported only here, the settings window uses GTK4
    return screensaver.run(args.animation)


def cmd_stop(_args):
    try:
        with open(pid_path()) as f:
            try:
                fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
                return 0  # nobody holds the lock, so the pid in the file is stale
            except OSError:
                pass
            os.kill(int(f.read().strip()), signal.SIGTERM)
    except (OSError, ValueError):
        pass  # not running
    return 0


def cmd_idle(args):
    """Start the screensaver after the configured idle time (run by the systemd user service)."""
    exe = shlex.quote(os.path.abspath(sys.argv[0]))
    seconds = max(60, config.load()["idle_minutes"] * 60)
    # No -w: swayidle must not wait for the screensaver to exit.
    cmd = ["swayidle", "timeout", str(seconds), f"{exe} run", "resume", f"{exe} stop"]
    if args.print:
        print(shlex.join(cmd))
        return 0
    if not shutil.which("swayidle"):
        sys.exit("xway-screensaver: swayidle is not installed")
    os.execvp(cmd[0], cmd)


def cmd_settings(_args):
    from . import settings  # GTK4
    return settings.run()


def cmd_list(_args):
    for anim in animations.ALL:
        print(f"{anim.NAME:12} {anim.LABEL}")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(prog="xway-screensaver",
                                     description="Neon screensaver animations for Wayland desktops.")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command")
    run = sub.add_parser("run", help="show the screensaver now (the default)")
    run.add_argument("animation", nargs="?", choices=list(animations.BY_NAME),
                     help="override the configured animation")
    run.set_defaults(func=cmd_run)
    sub.add_parser("stop", help="close a running screensaver").set_defaults(func=cmd_stop)
    idle = sub.add_parser("idle", help="start the screensaver when the session goes idle")
    idle.add_argument("--print", action="store_true", help="print the swayidle command and exit")
    idle.set_defaults(func=cmd_idle)
    sub.add_parser("settings", help="open the settings window").set_defaults(func=cmd_settings)
    sub.add_parser("list", help="list the animations").set_defaults(func=cmd_list)

    args = parser.parse_args(argv)
    if args.command is None:
        args = parser.parse_args(["run", *(argv or [])])
    return args.func(args)

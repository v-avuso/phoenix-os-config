#!/usr/bin/env python3
"""Small, fixed-command adapters for Phoenix's Timewall/Caelestia session."""

from contextlib import contextmanager
from datetime import datetime
import fcntl
import os
from pathlib import Path
import stat
import subprocess
import sys

LOCK_NAME = "phoenix-wallpaper-theme.lock"
COMMAND_TIMEOUT = 30


def log(message):
    print(message, file=sys.stderr, flush=True)


@contextmanager
def wallpaper_theme_lock():
    runtime_dir = os.environ.get("XDG_RUNTIME_DIR")
    if not runtime_dir:
        raise RuntimeError("XDG_RUNTIME_DIR is unavailable")
    runtime_stat = os.stat(runtime_dir)
    if (
        not stat.S_ISDIR(runtime_stat.st_mode)
        or runtime_stat.st_uid != os.getuid()
        or runtime_stat.st_mode & 0o077
    ):
        raise RuntimeError("XDG_RUNTIME_DIR is not a private directory owned by this user")
    lock_path = Path(runtime_dir) / LOCK_NAME
    flags = os.O_CREAT | os.O_RDWR | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(lock_path, flags, 0o600)
    locked = False
    try:
        lock_stat = os.fstat(fd)
        if (
            not stat.S_ISREG(lock_stat.st_mode)
            or lock_stat.st_uid != os.getuid()
            or lock_stat.st_mode & 0o077
        ):
            raise RuntimeError("wallpaper/theme lock is not a private regular file owned by this user")
        fcntl.flock(fd, fcntl.LOCK_EX)
        locked = True
        yield
    finally:
        try:
            if locked:
                fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)


def run_short_command(argv, runner=subprocess.run):
    try:
        return runner(argv, check=False, timeout=COMMAND_TIMEOUT).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def wallpaper_command(caelestia, image, runner=subprocess.run):
    return run_short_command(
        [caelestia, "wallpaper", "-f", str(image), "--no-smart"], runner
    )


def set_fallback(caelestia, fallback, runner=subprocess.run):
    if not wallpaper_command(caelestia, fallback, runner):
        log("Caelestia could not apply the generated black wallpaper fallback")
        return False
    return True


def is_readable_regular_file(path):
    try:
        before = os.stat(path)
        if not stat.S_ISREG(before.st_mode):
            return False
        flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NONBLOCK", 0)
        fd = os.open(path, flags)
    except OSError:
        return False
    try:
        opened = os.fstat(fd)
        return (
            stat.S_ISREG(opened.st_mode)
            and (opened.st_dev, opened.st_ino) == (before.st_dev, before.st_ino)
        )
    except OSError:
        return False
    finally:
        os.close(fd)


def start_timewall(timewall, wallpaper, caelestia, fallback, runner=subprocess.run):
    if not is_readable_regular_file(wallpaper):
        log("Dynamic wallpaper is missing, unreadable, or not a regular file; using black fallback")
        try:
            with wallpaper_theme_lock():
                set_fallback(caelestia, fallback, runner)
        except (OSError, RuntimeError) as error:
            log(f"Wallpaper fallback could not acquire its session lock: {error}")
        return 0

    try:
        result = runner(
            [timewall, "set", "--daemon", wallpaper],
            check=False,
        )
    except OSError:
        result = None
    if result is not None and result.returncode == 0:
        return 0

    status = "could not start" if result is None else f"exited with status {result.returncode}"
    log(f"Timewall {status}; using black fallback")
    try:
        with wallpaper_theme_lock():
            set_fallback(caelestia, fallback, runner)
    except (OSError, RuntimeError) as error:
        log(f"Wallpaper fallback could not acquire its session lock: {error}")
    # A broken/missing third-party wallpaper is an expected fallback case.
    # Returning success prevents a systemd restart loop.
    return 0


def set_wallpaper(caelestia, fallback, image, runner=subprocess.run):
    try:
        with wallpaper_theme_lock():
            if wallpaper_command(caelestia, image, runner):
                return 0
            log("Caelestia wallpaper setter failed; using black fallback")
            return 0 if set_fallback(caelestia, fallback, runner) else 1
    except (OSError, RuntimeError) as error:
        log(f"Wallpaper setter could not acquire its session lock: {error}")
        return 1


def _minutes(value):
    hour, minute = (int(part) for part in value.split(":"))
    if not (0 <= hour < 24 and 0 <= minute < 60):
        raise ValueError("theme boundaries must use valid local HH:MM times")
    return hour * 60 + minute


def theme_mode(local_time=None, light_at="07:00", dark_at="20:00"):
    local_time = local_time or datetime.now().astimezone().time()
    current = local_time.hour * 60 + local_time.minute
    return "light" if _minutes(light_at) <= current < _minutes(dark_at) else "dark"


def sync_theme(caelestia, light_at="07:00", dark_at="20:00", runner=subprocess.run, local_time=None):
    mode = theme_mode(local_time, light_at, dark_at)
    try:
        with wallpaper_theme_lock():
            if run_short_command([caelestia, "scheme", "set", "-m", mode], runner):
                return 0
            log(f"Caelestia could not apply the {mode} theme mode")
            return 1
    except (OSError, RuntimeError) as error:
        log(f"Theme update could not acquire its session lock: {error}")
        return 1


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    if args and args[0] == "start" and len(args) == 5:
        return start_timewall(*args[1:])
    if args and args[0] == "set-wallpaper" and len(args) == 4:
        return set_wallpaper(*args[1:])
    if args and args[0] == "sync-theme" and len(args) == 4:
        return sync_theme(args[1], args[2], args[3])
    log("Invalid Phoenix Timewall helper invocation")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

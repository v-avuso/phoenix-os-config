"""Describe the supported history layout without reading or migrating user data.

Run against retained homes only after identifying the old sandbox. This helper
does not stop clients, move databases, import tasks, or authorize activation.
"""
import argparse
import json
from pathlib import Path
import stat


ROLLOUT_DIRS = ("sessions", "archived_sessions", "thread-writer-locks")
# Exact Codex 0.159 SqliteConfig filenames; never enumerate a whole profile.
DATABASES = ("state_5.sqlite", "thread_history_1.sqlite", "goals_1.sqlite",
             "memories_1.sqlite", "queue_1.sqlite", "logs_2.sqlite")


def checked_path(value):
    path = Path(value)
    if not path.is_absolute() or ".." in path.parts:
        raise ValueError("history paths must be absolute and normalized")
    for parent in (*reversed(path.parents), path):
        try:
            mode = parent.lstat().st_mode
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(mode):
            raise ValueError("history paths must not contain symlinks")
    return path


def inventory(home):
    home = checked_path(home)
    if not home.is_dir():
        raise ValueError("retained Codex home must be an existing directory")
    result = {"codex_home": str(home), "rollout_directories": {}, "databases": []}
    for name in ROLLOUT_DIRS:
        path = checked_path(home / name)
        if path.exists() and not path.is_dir():
            raise ValueError("rollout location must be a directory")
        result["rollout_directories"][name] = path.is_dir()
    for name in DATABASES:
        for suffix in ("", "-wal", "-shm"):
            path = checked_path(home / (name + suffix))
            if path.exists():
                if not path.is_file():
                    raise ValueError("database location must be a regular file")
                result["databases"].append(path.name)
    return result


def plan(native_home, sqlite_home, retained_homes):
    native = inventory(native_home)
    sqlite = checked_path(sqlite_home)
    if sqlite == Path(native["codex_home"]) or sqlite.is_relative_to(Path(native["codex_home"])):
        raise ValueError("shared SQLite home must be separate from the Native profile")
    if sqlite.exists() and not sqlite.is_dir():
        raise ValueError("shared SQLite location must be a directory")
    return {
        "schema": 1,
        "status": "plan-only",
        "native": native,
        "retained_sandboxes": [inventory(home) for home in retained_homes],
        "shared_sqlite_home": str(sqlite),
        "sandbox_codex_home": native["codex_home"],
        "sandbox_bind_directories": [str(Path(native["codex_home"]) / name) for name in ROLLOUT_DIRS] + [str(sqlite)],
        "required_before_activation": [
            "Exit every Native and sandbox Codex writer in a coordinated handoff.",
            "Preserve complete old homes; relocate only the allowlisted Native SQLite families while stopped.",
            "Retain sandbox databases and rollouts; use upstream thread resume for selected retained tasks and verify their IDs.",
            "Verify Native and sandbox listing, resume, archive, and writer exclusion before recording migration readiness.",
        ],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native-home", required=True)
    parser.add_argument("--sqlite-home", required=True)
    parser.add_argument("--retained-home", action="append", default=[])
    args = parser.parse_args()
    try:
        print(json.dumps(plan(args.native_home, args.sqlite_home, args.retained_home), indent=2))
    except ValueError as error:
        parser.exit(1, str(error) + "\n")

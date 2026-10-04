"""Conditional upstream history locations and cold-handoff preflight.

Uses SQLite's backup API to prepare new databases; source databases stay intact.
No importer, synchronizer, or profile reconciliation.
"""
import argparse
from contextlib import closing
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sqlite3
import stat
import sys
import tomllib

DATABASES = {"state_5.sqlite", "thread_history_1.sqlite", "goals_1.sqlite",
             "memories_1.sqlite", "queue_1.sqlite", "logs_2.sqlite"}
DIRECTORIES = ("sessions", "archived_sessions", "thread-writer-locks")


def lifecycle_lock(config, *, shared=False):
    parent = regular_path(Path(config["root"]).parent, directory=True)
    parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    path = regular_path(parent / "history.lock")
    fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid():
            raise ValueError("history lifecycle lock has unexpected ownership or type")
        fcntl.flock(fd, (fcntl.LOCK_SH if shared else fcntl.LOCK_EX) | fcntl.LOCK_NB)
        os.set_inheritable(fd, True)
        return fd
    except BlockingIOError:
        os.close(fd)
        raise ValueError("history lifecycle is busy; keep clients stopped for the cold handoff") from None
    except BaseException:
        os.close(fd)
        raise


def regular_path(value, *, directory=False, required=False):
    path = Path(value)
    if not path.is_absolute() or ".." in path.parts:
        raise ValueError("history location must be absolute and normalized")
    for item in (*reversed(path.parents), path):
        try:
            mode = item.lstat().st_mode
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(mode):
            raise ValueError("history location must not contain symlinks")
    if path.exists():
        mode = path.stat().st_mode
        if not (stat.S_ISDIR(mode) if directory else stat.S_ISREG(mode)):
            raise ValueError("history location has an unexpected file type")
    elif required:
        raise ValueError("required shared history location is missing")
    return path


def reject_overrides(home):
    path = regular_path(home / "config.toml")
    if not path.exists():
        return
    with path.open("rb") as stream:
        config = tomllib.load(stream)
    profiles = config.get("profiles", {})
    if "sqlite_home" in config or any("sqlite_home" in profile for profile in profiles.values() if isinstance(profile, dict)):
        raise ValueError("remove the Native sqlite_home configuration override before sharing history")


def status(config):
    home = regular_path(config["nativeHome"], directory=True)
    root = regular_path(config["root"], directory=True)
    ready = regular_path(root / "ready.json")
    journal = regular_path(root / "migration.json")
    transition = regular_path(home / ".phoenix-history-shared")
    preparing = regular_path(str(root) + ".preparing", directory=True)
    if preparing.exists():
        raise ValueError("cold history preparation is in progress; keep clients stopped")
    if not ready.exists():
        if journal.exists() or transition.exists() or root.exists():
            raise ValueError("history handoff is incomplete; restore validated readiness before launching")
        return {"active": False}
    reject_overrides(home)
    sqlite = regular_path(root / "sqlite", directory=True, required=True)
    marker = json.loads(ready.read_text())
    if not isinstance(marker, dict):
        raise ValueError("invalid shared history readiness metadata")
    if (marker.get("schema") != 1 or marker.get("nativeHome") != str(home)
            or marker.get("sqliteHome") != str(sqlite)):
        raise ValueError("shared history readiness does not match the configured locations")
    names = marker.get("databases")
    if not isinstance(names, list) or not names or "state_5.sqlite" not in names or not all(isinstance(name, str) and name in DATABASES for name in names):
        raise ValueError("shared history readiness must identify the migrated upstream databases")
    for name in names:
        regular_path(sqlite / name, required=True)
    for item in sqlite.iterdir():
        base = item.name.removesuffix("-wal").removesuffix("-shm")
        if base not in DATABASES:
            raise ValueError("unknown file in credential-free shared SQLite directory")
        regular_path(item)
    for name in DIRECTORIES:
        regular_path(home / name, directory=True, required=True)
    return {"active": True, "codexHome": str(home), "sqliteHome": str(sqlite)}


def cold_preflight(config, proc=Path("/proc")):
    home = regular_path(config["nativeHome"], directory=True, required=True)
    reject_overrides(home)
    reject_writers(proc)
    for item in home.iterdir():
        if ".sqlite" in item.name:
            base = item.name.removesuffix("-wal").removesuffix("-shm")
            if base not in DATABASES:
                raise ValueError("unknown Native SQLite family; review the exact upstream version first")
            regular_path(item)
    root = regular_path(config["root"], directory=True)
    if root.exists() or Path(str(root) + ".preparing").exists():
        raise ValueError("history destination already exists; recover or review it before retrying")
    if root == home or root.is_relative_to(home):
        raise ValueError("shared SQLite location must be separate from the Native profile")
    for name in DIRECTORIES:
        regular_path(home / name, directory=True, required=True)
    regular_path(home / "state_5.sqlite", required=True)
    return {"status": "cold-preflight-only", "applySupported": True,
            "next": "Explicit --apply backs up known Native databases through SQLite and publishes shared history atomically; retained sandbox history stays separate."}


def enable(config, *, apply=False, proc=Path("/proc"), backup=None):
    reject_writers(proc)
    fd = lifecycle_lock(config)
    try:
        return prepare(config, apply=apply, proc=proc, backup=backup)
    finally:
        os.close(fd)


def prepare(config, *, apply=False, proc=Path("/proc"), backup=None):
    result = cold_preflight(config, proc)
    if not apply:
        return result
    home, root = Path(config["nativeHome"]), Path(config["root"])
    root.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    preparing = Path(str(root) + ".preparing")
    preparing.mkdir(mode=0o700)
    try:
        # This visible staging directory also makes the reviewed entry points
        # refuse new clients while all databases are being backed up.
        sqlite = preparing / "sqlite"
        sqlite.mkdir(mode=0o700)
        names = []
        for name in sorted(DATABASES):
            source = regular_path(home / name)
            if not source.exists():
                continue
            # Re-check writers without cold_preflight's destination check.
            reject_writers(proc)
            target = sqlite / name
            if backup is not None:
                backup(source, target)
            else:
                with closing(sqlite3.connect(source.as_uri() + "?mode=ro", uri=True)) as original:
                    with closing(sqlite3.connect(target)) as copied:
                        original.backup(copied)
                        if copied.execute("PRAGMA quick_check").fetchone() != ("ok",):
                            raise ValueError("prepared SQLite backup failed integrity validation")
            target.chmod(0o600)
            names.append(name)
        marker = {"schema": 1, "nativeHome": str(home),
                  "sqliteHome": str(root / "sqlite"), "databases": names,
                  "retainedSandboxHistory": "separate; preserved unchanged"}
        ready = preparing / "ready.json"
        ready.write_text(json.dumps(marker) + "\n")
        ready.chmod(0o600)
        # Flush the complete prepared tree before publishing the directory.
        for path in [*sqlite.iterdir(), ready, sqlite, preparing]:
            fd = os.open(path, os.O_RDONLY)
            try:
                os.fsync(fd)
            finally:
                os.close(fd)
        reject_writers(proc)
        if root.exists():
            raise ValueError("history destination appeared during preparation")
        preparing.rename(root)
        fd = os.open(root.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    except BaseException:
        if preparing.exists():
            shutil.rmtree(preparing)
        raise
    return {"status": "enabled", "retainedSandboxHistory": "separate; preserved unchanged",
            "validation": "restart both clients and verify listing, resume, archive, and writer exclusion"}


def reject_writers(proc):
    # comm first avoids probing unrelated browser namespaces. cmdline is read
    # only for Electron/Python/shell launchers, is bounded, and never printed.
    for process in proc.iterdir():
        if not process.name.isdigit():
            continue
        try:
            if process.stat().st_uid != os.getuid():
                continue
            command = (process / "comm").read_text().strip().lower()
            relevant = "codex" in command
            if not relevant and command in {"electron", "python", "python3", "bash", "sh"}:
                try:
                    with (process / "cmdline").open("rb") as stream:
                        arguments = stream.read(8192).split(b"\0")[:4]
                    relevant = any(b"/bin/codex" in arg.lower() or b"codex-desktop" in arg.lower() for arg in arguments)
                except PermissionError:
                    # An unrelated inaccessible generic interpreter is not
                    # evidence of a Codex writer. Named Codex processes fail.
                    continue
            if relevant:
                raise ValueError("cold history handoff requires exiting every same-user Codex process")
        except FileNotFoundError:
            continue
        except PermissionError:
            continue


def recover_staging(config, *, proc=Path("/proc")):
    reject_writers(proc)
    fd = lifecycle_lock(config)
    try:
        root = regular_path(config["root"], directory=True)
        staging = regular_path(str(root) + ".preparing", directory=True, required=True)
        if root.exists():
            raise ValueError("published history exists; staging recovery cannot alter it")
        for path in (staging, staging / "sqlite"):
            regular_path(path, directory=True, required=True)
            info = path.stat()
            if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o700:
                raise ValueError("staging recovery requires owned private directories")
        if any(path.name not in {"sqlite", "ready.json"} for path in staging.iterdir()):
            raise ValueError("unexpected staging entry; manual review required")
        for path in (staging / "sqlite").iterdir():
            base = path.name.removesuffix("-wal").removesuffix("-shm").removesuffix("-journal")
            if base not in DATABASES:
                raise ValueError("unknown staging SQLite family; manual review required")
            regular_path(path, required=True)
            if path.stat().st_uid != os.getuid():
                raise ValueError("staging file has unexpected ownership")
        ready = regular_path(staging / "ready.json")
        if ready.exists() and ready.stat().st_uid != os.getuid():
            raise ValueError("staging metadata has unexpected ownership")
        reject_writers(proc)
        shutil.rmtree(staging)
        return {"status": "unpublished-staging-removed", "sourceDatabases": "unchanged"}
    finally:
        os.close(fd)


def has_sqlite_override(args):
    for index, value in enumerate(args):
        candidate = value.removeprefix("--config=") if value.startswith("--config=") else (
            args[index + 1] if value in ("-c", "--config") and index + 1 < len(args) else "")
        if candidate.split("=", 1)[0].strip().split(".")[-1] == "sqlite_home":
            return True
    return False


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config")
    parser.add_argument("--cold-preflight", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--recover-staging", action="store_true")
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    with open(args.config) as stream:
        config = json.load(stream)
    try:
        if args.recover_staging:
            print(json.dumps(recover_staging(config)))
            return
        if args.cold_preflight or args.apply:
            print(json.dumps(enable(config, apply=args.apply)))
            return
        command = args.command
        if command[:1] == ["--"]:
            command = command[1:]
        # The configured host supervisor holds this for the client's lifetime.
        # Status-only calls are already covered by the sandbox launcher lock.
        if command:
            lock = lifecycle_lock(config, shared=True)
        selected = status(config)
        if not command:
            print(json.dumps(selected))
            return
        env = dict(os.environ)
        if selected["active"]:
            if has_sqlite_override(command[1:]):
                raise ValueError("shared history entry points do not accept sqlite_home overrides")
            env["CODEX_HOME"] = selected["codexHome"]
            env["CODEX_SQLITE_HOME"] = selected["sqliteHome"]
        if config.get("transportHelper"):
            # Keep ownership outside FHS/Electron launchers, which may close
            # inherited descriptors. Reuse the sandbox transport supervisor.
            spec = importlib.util.spec_from_file_location("phoenix_transport", config["transportHelper"])
            helper = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(helper)
            result = helper.locked_transport(command, env, lock)
            raise SystemExit(result if result >= 0 else 128 - result)
        os.execve(command[0], command, env)
    except (ValueError, OSError, json.JSONDecodeError, tomllib.TOMLDecodeError) as error:
        parser.exit(1, "Phoenix history unavailable: " + str(error) + "\n")


if __name__ == "__main__":
    main()

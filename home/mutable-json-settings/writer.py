"""Deploy one writable application JSON baseline; preserve existing experiments at boot."""

import argparse
import json
import os
from pathlib import Path
import stat
import tempfile


def deploy(baseline: Path, target: Path, mode: str, expected_type: str = "object") -> None:
    content = baseline.read_bytes()
    declared = json.loads(content)
    root_type = {"object": dict, "array": list}[expected_type]
    if not isinstance(declared, root_type):
        raise ValueError(f"Baseline must be a JSON {expected_type}")

    target.parent.mkdir(parents=True, exist_ok=True)
    if target.parent.stat().st_uid != os.getuid():
        raise ValueError(f"Settings directory is not owned by the current user: {target.parent}")
    try:
        existing = target.lstat()
    except FileNotFoundError:
        existing = None

    if existing is not None:
        if existing.st_uid != os.getuid():
            raise ValueError(f"Settings path is not owned by the current user: {target}")
        if stat.S_ISREG(existing.st_mode):
            # Ownership permits restoring write access even for old read-only files.
            target.chmod(stat.S_IMODE(existing.st_mode) | stat.S_IRUSR | stat.S_IWUSR)
            if mode == "preserve":
                return
            try:
                # Python equates True and 1; canonical JSON retains JSON types.
                canonical = lambda value: json.dumps(value, sort_keys=True, separators=(",", ":"))
                if canonical(json.loads(target.read_bytes())) == canonical(declared):
                    return
            except (ValueError, UnicodeDecodeError):
                pass
        elif not stat.S_ISLNK(existing.st_mode):
            raise ValueError(f"Settings path is not a regular file or legacy symlink: {target}")

    # Replace legacy store symlinks without writing through them. Atomic rename
    # also avoids partial JSON. Callers must support replacement file events.
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=target.parent, prefix=f".{target.name}.", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
            os.fchmod(stream.fileno(), 0o644)
        os.replace(temporary, target)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["preserve", "reassert"])
    parser.add_argument("baseline", type=Path)
    parser.add_argument("target", type=Path)
    parser.add_argument("expected_type", choices=["object", "array"])
    args = parser.parse_args()
    try:
        deploy(args.baseline, args.target, args.mode, args.expected_type)
    except (OSError, ValueError) as error:
        parser.exit(1, f"Mutable JSON settings: {error}\n")

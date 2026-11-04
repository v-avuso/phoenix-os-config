"""Own exactly one reserved add-on symlink; never reconcile the AddOns tree."""
import argparse
import os
from pathlib import Path
import re
import tempfile

NAME = "PhoenixWoWToolkit"
OWNED = re.compile(r"/nix/store/[a-z0-9]{32}-phoenix-wow-toolkit/PhoenixWoWToolkit")


def deploy(destination, source=None):
    destination = Path(destination)
    if not destination.is_dir():
        print(f"Phoenix WoW Toolkit: skip missing AddOns directory: {destination}")
        return
    target = destination / NAME
    if os.path.lexists(target):
        if not target.is_symlink() or not OWNED.fullmatch(os.readlink(target)):
            print(f"Phoenix WoW Toolkit: preserve unmanaged collision: {target}")
            return
        if source is None:
            target.unlink()
            return
        if os.readlink(target) == str(source):
            return
    elif source is None:
        return
    if not OWNED.fullmatch(str(source)) or not (Path(source) / (NAME + ".toc")).is_file():
        raise ValueError("Expected a built Phoenix toolkit store directory with its TOC")
    # Same-filesystem replacement keeps an existing managed deployment intact on failure.
    with tempfile.TemporaryDirectory(prefix=".phoenix-toolkit-", dir=destination) as temporary:
        link = Path(temporary) / NAME
        link.symlink_to(source)
        os.replace(link, target)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination")
    parser.add_argument("source", nargs="?", help="Omit to remove only a managed toolkit link")
    args = parser.parse_args()
    deploy(args.destination, args.source)

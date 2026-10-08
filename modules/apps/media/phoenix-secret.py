#!/usr/bin/env python3
"""Store or inspect Phoenix desktop secrets without displaying their values."""

from __future__ import annotations

import getpass
import subprocess
import sys


SERVICE = "phoenix-media"
KEY = "acoustid-client"
LABEL = "Phoenix AcoustID application key"
SECRET_TOOL = "secret-tool"
SECRET_TOOL_TIMEOUT = 60


def run_secret_tool(action: str, *, secret: str | None = None) -> subprocess.CompletedProcess[str]:
    command = [SECRET_TOOL, action]
    if action == "store":
        command.append(f"--label={LABEL}")
    command.extend(["service", SERVICE, "key", KEY])
    return subprocess.run(
        command,
        input=secret,
        capture_output=True,
        text=True,
        timeout=SECRET_TOOL_TIMEOUT,
        check=False,
    )


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if args not in (["set", "acoustid"], ["check", "acoustid"], ["delete", "acoustid"]):
        print("Usage: phoenix-secret {set|check|delete} acoustid", file=sys.stderr)
        return 2

    action = args[0]
    if action == "set":
        if not sys.stdin.isatty() or not sys.stderr.isatty():
            print("Set requires an interactive terminal for hidden input.", file=sys.stderr)
            return 2
        secret = getpass.getpass("AcoustID client key: ")
        if not secret.strip():
            print("No key entered; nothing stored.", file=sys.stderr)
            return 2
        try:
            result = run_secret_tool("store", secret=secret)
        except (OSError, subprocess.TimeoutExpired):
            result = None
        if result is None or result.returncode != 0:
            print("Could not store the key in GNOME Keyring.", file=sys.stderr)
            return 1
        print("AcoustID client key stored.")
        return 0

    if action == "check":
        try:
            result = run_secret_tool("lookup")
        except (OSError, subprocess.TimeoutExpired):
            result = None
        available = result is not None and result.returncode == 0 and bool(result.stdout.strip())
        print("AcoustID client key is available." if available else "AcoustID client key is not available.")
        return 0 if available else 1

    try:
        result = run_secret_tool("clear")
    except (OSError, subprocess.TimeoutExpired):
        result = None
    if result is None or result.returncode != 0:
        print("Could not delete the AcoustID client key.", file=sys.stderr)
        return 1
    print("AcoustID client key deleted if it was present.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

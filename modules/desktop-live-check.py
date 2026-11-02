"""Refuse replacing a compositor beneath an existing graphical session."""
from pathlib import Path
import sys


def check(candidate, proc=Path('/proc')):
    expected = Path(candidate).resolve(strict=True)
    # The pinned Nixpkgs package uses a compiled wrapper that execs this sibling.
    wrapped = expected.with_name('.Hyprland-wrapped')
    if wrapped.exists():
        expected = wrapped.resolve(strict=True)
    for process in proc.iterdir():
        if not process.name.isdecimal():
            continue
        try:
            # Linux truncates the executable's comm field to 15 characters.
            if process.joinpath('comm').read_text().strip() not in {'Hyprland', '.Hyprland-wrapp'}:
                continue
            running = process.joinpath('exe').resolve(strict=True)
        except FileNotFoundError:
            if process.exists():
                raise ValueError('Phoenix cannot inspect an existing process; live activation stopped.') from None
            continue  # Process exited during inspection.
        if running != expected:
            raise ValueError(
                'Phoenix stopped live activation: an existing Hyprland session uses '
                'a different compositor build. Use phoenix-boot and reboot when '
                'convenient; the running session has not been restarted.')


if __name__ == '__main__':
    try:
        check(sys.argv[1])
    except (OSError, ValueError) as error:
        raise SystemExit(str(error)) from None

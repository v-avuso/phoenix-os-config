"""Use Hue's explicit display preference; delegate all other requests unchanged."""
import argparse
import json
import os
import subprocess
import sys
from sources import APP_ID, automatic_selection, monitors, preference_path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--picker', required=True)
    parser.add_argument('--hyprctl', required=True)
    args, forwarded = parser.parse_known_args()
    if os.environ.get('XDPH_APP_ID') == APP_ID:
        try:
            preference = json.loads(preference_path().read_text())
            selection = automatic_selection(APP_ID, preference, monitors(args.hyprctl))
            if selection:
                sys.stdout.write(selection)
                return
        except (OSError, ValueError, KeyError, subprocess.SubprocessError):
            pass  # Missing preference/output: retain the full native chooser.
    os.execv(args.picker, [args.picker, *forwarded])


if __name__ == '__main__':
    main()

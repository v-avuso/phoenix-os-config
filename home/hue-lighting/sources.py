"""Hue-only source preferences shared by the controller and portal picker."""
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

APP_ID = 'org.phoenix.HueSync'


def monitors(hyprctl='hyprctl'):
    data = json.loads(subprocess.check_output([hyprctl, '-j', 'monitors'], timeout=2))
    if not isinstance(data, list):
        raise ValueError('Invalid display list')
    for monitor in data:
        if (not isinstance(monitor, dict) or not isinstance(monitor.get('name'), str)
                or not re.fullmatch(r'[A-Za-z0-9_.:-]+', monitor['name'])
                or type(monitor.get('x')) is not int or type(monitor.get('y')) is not int):
            raise ValueError('Invalid display metadata')
    return sorted([m for m in data if not m.get('disabled', False)],
                  key=lambda m: (m['x'], m['y'], m['name']))


def default_monitor(displays, position):
    if not 1 <= position <= len(displays):
        raise ValueError('The configured default display is unavailable. Select a connected display.')
    return displays[position - 1]['name']


def preference_path():
    return Path(os.environ['XDG_RUNTIME_DIR']) / 'phoenix-hue-control' / 'source.json'


def write_preference(value):
    path = preference_path()
    path.parent.mkdir(mode=0o700, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', dir=path.parent, delete=False) as output:
            temporary = Path(output.name)
            json.dump(value, output)
        temporary.replace(path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def automatic_selection(app_id, preference, displays):
    # App IDs route desktop UX; unsandboxed same-user apps can impersonate them.
    # Never interpret an empty/missing app ID as Hue.
    if app_id != APP_ID or not isinstance(preference, dict) or preference.get('mode') != 'screen':
        return None
    output = preference.get('output')
    if output not in {m['name'] for m in displays}:
        return None
    # No restore flag: resolve the configured default against live outputs on
    # each start, rather than saving a connector-bound portal restore token.
    return '[SELECTION]/screen:' + output + '\n'

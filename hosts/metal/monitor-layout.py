#!/usr/bin/env python3
"""Apply preferred modes and reflow available displays in physical order."""

import json
import math
import subprocess
import sys


layout_path, kscreen_doctor = sys.argv[1:3]
with open(layout_path, encoding="utf-8") as layout_file:
    layout = json.load(layout_file)

config = json.loads(subprocess.check_output([kscreen_doctor, "-j"], text=True))
outputs = {
    output.get("name"): output
    for output in config.get("outputs", [])
    if output.get("connected") and output.get("enabled")
}

def find_mode(output, preferred):
    """Choose the requested mode, allowing normal fractional refresh timings."""
    modes = output.get("modes", [])
    candidates = [
        mode
        for mode in modes
        if mode.get("size", {}).get("width") == preferred["width"]
        and mode.get("size", {}).get("height") == preferred["height"]
    ]
    if candidates:
        closest = min(
            candidates,
            key=lambda mode: abs(mode.get("refreshRate", 0) - preferred["refreshRate"]),
        )
        if abs(closest.get("refreshRate", 0) - preferred["refreshRate"]) <= 1:
            return closest

    # Keep the active valid mode when the requested resolution/refresh is absent.
    current_id = str(output.get("currentModeId", ""))
    current = next((mode for mode in modes if str(mode.get("id")) == current_id), None)
    if current is not None:
        return current

    # An output without a valid active mode can still be laid out using any mode
    # KScreen reports, rather than failing the whole hotplug reflow.
    preferred_ids = {str(mode_id) for mode_id in output.get("preferredModes", [])}
    return next(
        (mode for mode in modes if str(mode.get("id")) in preferred_ids),
        modes[0] if modes else None,
    )


x = 0
commands = []
for monitor in layout:
    output = outputs.get(monitor["connector"])
    if output is None:
        continue

    scale = monitor.get("scale", output.get("scale") or 1)
    if scale <= 0:
        continue

    mode = find_mode(output, monitor.get("preferredMode", {}))
    if mode is None:
        continue

    mode_size = mode.get("size") or {}
    width = mode_size.get("width")
    if not width:
        continue

    current_mode_id = str(output.get("currentModeId", ""))
    if str(mode.get("id")) != current_mode_id:
        commands.append(f"output.{monitor['connector']}.mode.{mode['id']}")
    if abs((output.get("scale") or 1) - scale) > 0.001:
        commands.append(f"output.{monitor['connector']}.scale.{scale}")

    # These panels are landscape. Divide the selected mode's pixel width by the
    # configured scale and round up to match KWin's logical screen geometry.
    logical_width = math.ceil(width / scale)
    position = output.get("pos") or {}
    if position.get("x") != x or position.get("y") != 0:
        commands.append(f"output.{monitor['connector']}.position.{x},0")
    x += logical_width

if commands:
    subprocess.run([kscreen_doctor, *commands], check=True)

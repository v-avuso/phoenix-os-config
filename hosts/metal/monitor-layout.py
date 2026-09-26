#!/usr/bin/env python3
"""Reflow the currently available phoenix displays in physical connector order."""

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

x = 0
commands = []
for monitor in layout:
    output = outputs.get(monitor["connector"])
    if output is None:
        continue

    size = output.get("size") or {}
    scale = output.get("scale") or 1
    width = size.get("width")
    if not width or scale <= 0:
        continue

    # These panels are currently landscape. KScreen reports pixel dimensions;
    # divide by scale and round up to match KWin's logical screen geometry.
    logical_width = math.ceil(width / scale)
    position = output.get("pos") or {}
    if position.get("x") != x or position.get("y") != 0:
        commands.append(f"output.{monitor['connector']}.position.{x},0")
    x += logical_width

if commands:
    subprocess.run([kscreen_doctor, *commands], check=True)

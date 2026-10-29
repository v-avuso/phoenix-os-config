"""Set TSM's native desktop-notification preference without replacing its config."""
import os
from pathlib import Path
import re
import sys
import tempfile
import tomllib

path = Path(sys.argv[1])
text = path.read_text() if path.exists() else ""
before = tomllib.loads(text)
if before.get("notifications_enabled") is False:
    sys.exit(0)
pattern = r"(?m)^notifications_enabled\s*=.*$"
updated = re.sub(pattern, "notifications_enabled = false", text)
if updated == text:
    updated = text + ("\n" if text and not text.endswith("\n") else "") + "notifications_enabled = false\n"
assert tomllib.loads(updated) == {**before, "notifications_enabled": False}
path.parent.mkdir(parents=True, exist_ok=True)
backup = path.with_name(path.name + ".before-notifications")
if path.exists() and not backup.exists():
    with open(backup, "x", opener=lambda name, flags: os.open(name, flags, 0o600)) as output:
        output.write(text)
with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, delete=False) as output:
    temporary = Path(output.name)
    output.write(updated)
try:
    temporary.replace(path)
finally:
    temporary.unlink(missing_ok=True)

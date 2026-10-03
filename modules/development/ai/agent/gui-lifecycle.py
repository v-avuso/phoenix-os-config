"""Use normal Linux quit after the last primary closes, with upstream wiring checks."""
import os
from pathlib import Path
import re
import sys
import tempfile

ID = r"[A-Za-z_$][A-Za-z0-9_$]*"
PREDICATE = re.compile(rf"function\s+({ID})\(\)\{{return\s+({ID})&&({ID})\?\.isReady\(\)===!0\}}")


def require_match(pattern, source, label):
    matches = list(pattern.finditer(source))
    if len(matches) != 1:
        raise ValueError(f"expected exactly one {label}; found {len(matches)}")
    return matches[0]


def inspect(source, build):
    predicate = require_match(PREDICATE, source, "tray-readiness predicate")
    name, visible, window = predicate.groups()
    prop = re.compile(rf"canHideLastWindowToTray\s*:\s*{re.escape(name)}\b")
    require_match(prop, source, "canHideLastWindowToTray consumer")
    close = re.compile(r"\.on\(([\"'`])close\1,([A-Za-z_$][\w$]*)=>\{(.*?)\}\);", re.S)
    handlers = [m for m in close.finditer(source)
                if "canHideLastWindowToTray?.()===!0" in m.group(3)]
    if len(handlers) != 1:
        raise ValueError(f"expected one close handler with tray guard; found {len(handlers)}")
    body = handlers[0].group(3)
    confirmation = body.find("shouldPreventClose(")
    bounds = body.find("persistPrimaryWindowBounds(")
    guard = body.find("canHideLastWindowToTray?.()===!0")
    if min(confirmation, bounds, guard) < 0 or not confirmation < bounds < guard:
        raise ValueError("close confirmation and bounds persistence must precede the tray guard")

    importer = re.compile(rf"\b({ID})\s*=\s*require\(([\"'])\./(bootstrap-[A-Za-z0-9_-]+\.js)\2\)")
    imported = require_match(importer, source, "bootstrap import")
    module, _, bootstrap_name = imported.groups()
    reference = re.compile(rf"\b{re.escape(module)}\.u\(\s*{re.escape(name)}\s*\)")
    require_match(reference, source, "bootstrap keepalive registration")
    bootstrap_path = build / bootstrap_name
    bootstrap = bootstrap_path.read_text()
    export = require_match(re.compile(rf"exports\.u\s*=\s*({ID})\b"), bootstrap,
                           "bootstrap u export")
    setter = export.group(1)
    set_state = require_match(re.compile(
        rf"function\s+{re.escape(setter)}\(({ID})\)\{{({ID})=\1\}}"),
        bootstrap, "bootstrap keepalive setter")
    state = set_state.group(2)
    linux_close = re.compile(
        rf"\.on\(([\"'`])window-all-closed\1,\(\)=>\{{process\.platform!==([\"'`])win32\2&&\("
        rf"process\.platform===([\"'`])darwin\3&&(?P<app>{ID})\.app\.isPackaged\|\|"
        rf"process\.platform===([\"'`])linux\5&&{re.escape(state)}\(\)\|\|"
        rf"(?P=app)\.app\.quit\(\)\)\}}\)")
    require_match(linux_close, bootstrap, "Linux window-all-closed keepalive consumer")
    electron = require_match(re.compile(
        rf"\b({ID})\s*=\s*require\(([\"'])electron\2\),{ID}=.{{0,40}}?\b\1=({ID})\.a\(\1\)"),
        source, "Electron default import")
    app = electron.group(1)
    interop = electron.group(3)
    if f"{interop}.a({app})" not in source:
        raise ValueError("Electron import interop is missing")
    if f"{app}.app.quit()" not in source:
        raise ValueError("Electron app.quit cleanup target is missing")
    register = require_match(re.compile(
        rf"registerWindow\(({ID}),({ID}),({ID}),({ID}),({ID})\)\{{(.*?)\}}trackPrimaryWindow\(", re.S),
        source, "registerWindow cleanup method")
    primary_window, _, primary_flag, _, _, method = register.groups()
    tracked = require_match(re.compile(
        rf"{re.escape(primary_flag)}&&this\.trackPrimaryWindow\({re.escape(primary_window)}\)"),
        method, "primary-window registration before close")
    listener = require_match(re.compile(
        rf"{re.escape(primary_window)}\.on\(([\"'`])closed\1,\(\)=>\{{(?P<body>[^{{}}]*)\}}\)"),
                             method, "closed cleanup listener")
    cleanup = require_match(re.compile(
        rf"{re.escape(primary_flag)}&&\(this\.primaryWindows\.delete\({re.escape(primary_window)}\),"
        rf"this\.lastActivePrimaryWindow==={re.escape(primary_window)}&&\(this\.lastActivePrimaryWindow=null\),"
        rf"this\.emitPrimaryWindowChangeIfNeeded\(\)\)"),
        method, "tracked-primary closed cleanup")
    if not (tracked.end() <= listener.start()
            and listener.start("body") <= cleanup.start()
            and cleanup.end() <= listener.end("body")):
        raise ValueError("tracked-primary cleanup must follow registration inside its closed listener")
    if f"{app}.app.quit()" in method:
        raise ValueError("Linux last-primary quit hook is already present")
    return predicate, name, visible, window, app, register, cleanup


def patch(root):
    root = Path(root)
    build = root / ".vite" / "build"
    mains = sorted(build.glob("main-*.js"))
    if not mains:
        raise ValueError(f"no main-*.js bundle under {build}")
    found = []
    sources = {}
    for path in mains:
        source = path.read_text()
        sources[path] = source
        for match in PREDICATE.finditer(source):
            found.append((path, match))
    if len(found) != 1:
        raise ValueError(f"expected exactly one tray-readiness predicate across main bundles; found {len(found)}")
    path, _ = found[0]
    source = sources[path]
    match, name, visible, window, app, register, cleanup = inspect(source, build)
    replacement = (f"function {name}(){{return process.platform!==`linux`&&{visible}&&"
                   f"{window}?.isReady()===!0}}")
    cleanup_end = register.start(6) + cleanup.end() - 1
    quit_hook = (f",process.platform===`linux`&&!this.isAppQuitting&&"
                 f"this.getPrimaryWindows().length===0&&{app}.app.quit()")
    edits = [(match.start(), match.end(), replacement), (cleanup_end, cleanup_end, quit_hook)]
    updated = source
    for start, end, text in sorted(edits, reverse=True):
        updated = updated[:start] + text + updated[end:]
    mode = path.stat().st_mode & 0o777
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         prefix=path.name + ".", delete=False) as out:
            temporary = Path(out.name)
            out.write(updated)
            out.flush()
            os.fsync(out.fileno())
        os.chmod(temporary, mode)
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return path


if __name__ == "__main__":
    try:
        if len(sys.argv) != 2:
            raise ValueError("usage: gui-lifecycle.py EXTRACTED_ASAR_ROOT")
        print(patch(sys.argv[1]))
    except (OSError, ValueError) as error:
        raise SystemExit(f"gui-lifecycle: {error}") from None

"""Isolate pinned desktop permission preferences; default ordinary work to Custom."""
from pathlib import Path
import sys

# Exact bundle owners/counts make a changed upstream layout fail before any write.
OWNERS = {
    ".vite/build/src-C1dW0Du8.js": (1, 0, 0, 0),
    "webview/assets/app-initial-b7dae1c6de39.js": (2, 2, 1, 3),
    "webview/assets/app-shared-f2257985f1b6.js": (1, 0, 0, 0),
    "webview/assets/pending-local-conversation-thread-da07ea601484.js": (1, 0, 0, 0),
}
KEYS = ("`agent-mode-by-host-id`", "`config-derived-agent-mode-by-host-id`",
        "`permission-selection-by-host-id:${e}`",
        "`preferred-non-full-access-agent-mode-by-host-id`")
LOOKUP = ("function Fci(e,t,n,r){let i=t[e];if(i!=null)return i;"
          "if(n&&r!=null&&t[r]===`guardian-approvals`)return`guardian-approvals`}")
# Thread-specific restricted/explicit policy outranks a stale host-wide preference.
# The upstream picker still applies a deliberate current-chat choice directly.
GUARDS = (
    "if(profile!=null&&profile!==`:workspace`&&profile!==`:read-only`)return;"
    "if(profile===`:read-only`)return`read-only`;"
    "if(mode!=null&&mode!==`auto`&&mode!==`guardian-approvals`){"
    "if([`read-only`,`custom`,`full-access`,`granular`].includes(mode))return mode;return;}"
)
REPLACEMENT = LOOKUP[:-1].replace("Fci(e,t,n,r)", "Fci(e,t,n,r,mode,profile)").replace(
    "{let i=t[e];", "{" + GUARDS + "let i=t[e];"
) + ";return`custom`}"

CALL = "pe=Fci(i,R,de,o)"


def patch(root):
    root = Path(root)
    changes = {}
    for name, counts in OWNERS.items():
        path = root / name
        source = path.read_text()
        if tuple(source.count(key) for key in KEYS) != counts:
            raise ValueError(f"Pinned permission preference owners changed: {name}")
        changes[path] = source
    # Reject additional owners, rather than leaving a shared writer unpatched.
    for path in list((root / ".vite/build").glob("*.js")) + list((root / "webview/assets").glob("*.js")):
        if path not in changes and any(key in path.read_text() for key in KEYS):
            raise ValueError(f"Unexpected permission preference owner: {path.name}")
    initial = root / "webview/assets/app-initial-b7dae1c6de39.js"
    source = changes[initial]
    if source.count(LOOKUP) != 1 or source.count(CALL) != 1:
        raise ValueError("Pinned permission preference/default seam changed")
    # Guard the upstream reconciliation that makes the default effective on resume.
    for seam in (
        "Ce=n!=null&&oe!=null&&(ae==null||ae.startsWith(`:`))&&(M!=null||pe!=null&&Sci(pe,P))&&oe!==_e",
        "Re=b||Ce?null:L?te:ae",
        "Be=b||Ce||ze||!I&&(L||ae==null&&oe!==`custom`)",
        "updateThreadPermissions(n,Te(e))",
    ):
        if source.count(seam) != 1:
            raise ValueError("Pinned resumed-thread permission reconciliation changed")
    changes[initial] = source.replace(LOOKUP, REPLACEMENT).replace(CALL, "pe=Fci(i,R,de,o,oe,ae)")
    for path, source in changes.items():
        for key in KEYS:
            source = source.replace(key, key.replace("`", "`phoenix-sandbox.", 1))
        changes[path] = source
    for path, source in changes.items():
        path.write_text(source)


if __name__ == "__main__":
    patch(sys.argv[1])

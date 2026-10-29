"""Isolate pinned desktop permission preferences; default ordinary work to Custom."""
from pathlib import Path
import re
import sys

# Reviewed owner/count fixtures. Runtime resolves generated filenames by family.
# Resolver bodies and reconciliation signatures remain explicit compatibility
# constraints: unmatched logic fails before writing any bundle; never weaken it.
OWNERS = {
    ".vite/build/src-C1dW0Du8.js": (1, 0, 0, 0),
    "webview/assets/app-initial-b7dae1c6de39.js": (2, 2, 1, 3),
    "webview/assets/app-shared-f2257985f1b6.js": (1, 0, 0, 0),
    "webview/assets/pending-local-conversation-thread-da07ea601484.js": (1, 0, 0, 0),
}
KEYS = ("`agent-mode-by-host-id`", "`config-derived-agent-mode-by-host-id`",
        "`permission-selection-by-host-id:${e}`",
        "`preferred-non-full-access-agent-mode-by-host-id`")
SELECTION_PREFIX = "permission-selection-by-host-id:"
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

NEW_OWNERS = {
    ".vite/build/src-Dtwb7yKT.js": (1, 0, 0, 0),
    "webview/assets/app-initial-a68277f60b93.js": (2, 2, 1, 3),
    "webview/assets/app-shared-61271c39e3c5.js": (1, 0, 0, 0),
    "webview/assets/pending-local-conversation-thread-cf20b4a98a86.js": (1, 0, 0, 0),
}
NEW_LOOKUP = ("function rSo(e,t,n,r,i){let a=t[e];if(a!=null&&a!==n[e])return a;"
              "if(r&&i!=null&&t[i]===`guardian-approvals`&&n[i]!==`guardian-approvals`)return`guardian-approvals`}")
NEW_CALL = "be=rSo(i,L,R,pe,o)"
NEW_REPLACEMENT = NEW_LOOKUP[:-1].replace("rSo(e,t,n,r,i)", "rSo(e,t,n,r,i,mode,profile)").replace(
    "{let a=t[e];", "{" + GUARDS + "let a=t[e];"
) + ";return`custom`}"
NEW_SEAMS = (
    "je=n!=null&&se!=null&&(oe==null||oe.startsWith(`:`))&&be!=null&&N.includes(be)&&se!==Te",
    "Je=b||we||je?null:I?ne:oe",
    "Ye=b||we||je||qe||!F&&(I||oe==null&&(se!==`custom`||ce?.type===`dangerFullAccess`))",
    "updateThreadPermissions(n,Ne(e))",
    "if(n!=null&&se!=null&&!b&&!we&&(nx(i)||be==null||!De||Oe))return",
)
# Official 26.1016.61520 retains the resolver/reconciliation bodies but renames
# their generated locals. Keep this reviewed variant explicit and fail closed.
CURRENT_CALL = "xe=rSo(i,R,z,me,o)"
CURRENT_SEAMS = (
    "Me=n!=null&&se!=null&&(oe==null||oe.startsWith(`:`))&&xe!=null&&P.includes(xe)&&se!==Ee",
    "Ye=b||Te||Me?null:L?ne:oe",
    "Xe=b||Te||Me||Je||!I&&(L||oe==null&&(se!==`custom`||ce?.type===`dangerFullAccess`))",
    "updateThreadPermissions(n,Pe(e))",
    "if(n!=null&&se!=null&&!b&&!Te&&(rx(i)||xe==null||!Oe||ke))return",
    "permissionOverrideThreadSettings:Je?Pe(se):null,permissionProfileId:oe,shouldSendPermissionOverrides:Je",
)
# Official 26.1021.22027 adds inherited defaults for new chats. Preserve that
# logic; only pass the renamed current-thread mode/profile to our resolver.
LATEST_CALL = "Ce=rSo(i,z,ee,ge,c)"
LATEST_SEAMS = (
    "Fe=n!=null&&le!=null&&(ce==null||ce.startsWith(`:`))&&Ce!=null&&F.includes(Ce)&&le!==ke",
    "Qe=S||Oe||Fe?null:R?ie:ce",
    "$e=S||Oe||Fe||Ze||!L&&!Te&&(R||ce==null&&(le!==`custom`||ue?.type===`dangerFullAccess`))",
    "updateThreadPermissions(n,Le(e))",
    "if(n!=null&&le!=null&&!S&&!Oe&&(zS(i)||Ce==null||!je||Me))return",
    "threadApprovalsReviewer:se,threadPermissionProfileId:ce,threadMode:le,threadSandboxPolicy:ue",
    "Te=R&&o&&!I&&!re.isSet",
    "permissionOverrideThreadSettings:Ze?Le(le):null,permissionProfileId:ce,shouldSendPermissionOverrides:Ze",
)
RECONCILIATION = {
    NEW_CALL: (NEW_SEAMS, ',se,oe)'),
    CURRENT_CALL: (CURRENT_SEAMS, ',se,oe)'),
    LATEST_CALL: (LATEST_SEAMS, ',le,ce)'),
}

IDENTIFIER = r'[A-Za-z_$][\w$]*'
TOKENS = re.compile(r'`[^`]*`|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|' + IDENTIFIER)
FIXED = {'null', 'if', 'return', 'updateThreadPermissions',
         'threadApprovalsReviewer', 'threadPermissionProfileId', 'threadMode',
         'threadSandboxPolicy', 'permissionOverrideThreadSettings',
         'permissionProfileId', 'shouldSendPermissionOverrides'}


def fragment(source, template, bindings):
    """Match exact operators/literals/properties and consistently renamed locals.

    This is deliberately a matcher for reviewed fragments, not a JavaScript
    parser. Bindings span the call and all reconciliation checks; distinct roles
    cannot collapse onto one variable. Unknown logic and ambiguous matches fail.
    """
    parts, groups, end = [], {}, 0
    for token in TOKENS.finditer(template):
        parts.append(re.escape(template[end:token.start()]))
        value = token[0]
        if (not re.fullmatch(IDENTIFIER, value) or value in FIXED or
                template[:token.start()].endswith('.')):
            parts.append(re.escape(value))
        elif value in bindings:
            parts.append(re.escape(bindings[value]))
        elif value in groups:
            parts.append('(?P=' + groups[value] + ')')
        else:
            group = 'v' + str(len(groups))
            groups[value] = group
            parts.append('(?P<' + group + '>' + IDENTIFIER + ')')
        end = token.end()
    parts.append(re.escape(template[end:]))
    matches = list(re.finditer(r'(?<![\w$])' + ''.join(parts) + r'(?![\w$])', source))
    if len(matches) != 1:
        raise ValueError('Pinned resumed-thread permission reconciliation changed')
    match = matches[0]
    updated = bindings | {name: match[group] for name, group in groups.items()}
    if len(set(updated.values())) != len(updated):
        raise ValueError('Permission reconciliation variable roles changed')
    return match[0], updated


def reconciliation(source, name):
    # Prefer the most specific reviewed contract. Earlier variants remain for
    # older pinned bundles; all operators and property names stay literal.
    for template, (seams, extra) in reversed(RECONCILIATION.items()):
        bindings = {'rSo': name}
        try:
            call, bindings = fragment(source, template, bindings)
            actual = []
            for seam in seams:
                matched, bindings = fragment(source, seam, bindings)
                actual.append(matched)
            mode, profile = extra.strip(',)').split(',')
            return call, actual, ',' + bindings[mode] + ',' + bindings[profile] + ')'
        except ValueError:
            continue
    raise ValueError('Pinned resumed-thread permission reconciliation changed')


def resolver(source):
    """Keep resolver bodies exact and bind their caller by reviewed structure."""
    for lookup, replacement, call, new in ((LOOKUP, REPLACEMENT, CALL, False),
                                           (NEW_LOOKUP, NEW_REPLACEMENT, NEW_CALL, True)):
        canonical = lookup.split('(', 1)[0].removeprefix('function ')
        pattern = re.escape(lookup).replace(re.escape(canonical), r'([A-Za-z_$][\w$]*)', 1)
        matches = list(re.finditer(pattern, source))
        if len(matches) == 1:
            name = matches[0].group(1)
            if new:
                call, _, _ = reconciliation(source, name)
            else:
                call = call.replace(canonical + '(', name + '(')
            return matches[0].group(), replacement.replace(canonical + '(', name + '('), call, new
    raise ValueError("Pinned permission preference/default seam changed")


def layout(root):
    """Resolve generated filenames by family and exhaustively checked key counts."""
    root = Path(root)
    families = (((".vite/build/src-*.js",), (1, 0, 0, 0)),
                (("webview/assets/app-initial-*.js",), (2, 2, 1, 3)),
                (("webview/assets/app-shared-*.js",), (1, 0, 0, 0)),
                (("webview/assets/pending-local-conversation-thread-*.js",
                  "webview/assets/local-conversation-thread-*.js"), (1, 0, 0, 0)))
    owners = {}
    for family, counts in families:
        matches = [path for pattern in family for path in root.glob(pattern)
                   if tuple(path.read_text().count(key) for key in KEYS) == counts]
        if len(matches) != 1:
            raise ValueError("Permission preference owner family changed: " + ', '.join(family))
        owners[str(matches[0].relative_to(root))] = counts
    initial = next(name for name in owners if '/app-initial-' in name)
    return owners, initial


def patch(root):
    root = Path(root)
    changes = {}
    owners, initial_name = layout(root)
    for name, counts in owners.items():
        path = root / name
        source = path.read_text()
        if tuple(source.count(key) for key in KEYS) != counts:
            raise ValueError(f"Pinned permission preference owners changed: {name}")
        if source.count(SELECTION_PREFIX) != source.count(KEYS[2]):
            raise ValueError(f"Unreviewed permission selection writer: {name}")
        changes[path] = source
    # Reject additional owners, rather than leaving a shared writer unpatched.
    for path in list((root / ".vite/build").glob("*.js")) + list((root / "webview/assets").glob("*.js")):
        if path not in changes and any(key in path.read_text() for key in (*KEYS, SELECTION_PREFIX)):
            raise ValueError(f"Unexpected permission preference owner: {path.name}")
    initial = root / initial_name
    source = changes[initial]
    lookup, replacement, call, new = resolver(source)
    if source.count(lookup) != 1 or source.count(call) != 1:
        raise ValueError("Pinned permission preference/default seam changed")
    # An undefined preference preserves the current thread through the upstream
    # early return, before the host-default fallback can emit permission overrides.
    # Guard both reconciliation and the preserved profile/override result.
    if new:
        name = lookup.split('(', 1)[0].removeprefix('function ')
        _, seams, extra = reconciliation(source, name)
    else:
        seams = (
            "Ce=n!=null&&oe!=null&&(ae==null||ae.startsWith(`:`))&&(M!=null||pe!=null&&Sci(pe,P))&&oe!==_e",
            "Re=b||Ce?null:L?te:ae",
            "Be=b||Ce||ze||!I&&(L||ae==null&&oe!==`custom`)",
            "updateThreadPermissions(n,Te(e))",
        )
        extra = ',oe,ae)'
    for seam in seams:
        if source.count(seam) != 1:
            raise ValueError("Pinned resumed-thread permission reconciliation changed")
    changes[initial] = source.replace(lookup, replacement).replace(call, call[:-1] + extra)
    for path, source in changes.items():
        for key in KEYS:
            source = source.replace(key, key.replace("`", "`phoenix-sandbox.", 1))
        changes[path] = source
    for path, source in changes.items():
        path.write_text(source)


if __name__ == "__main__":
    patch(sys.argv[1])

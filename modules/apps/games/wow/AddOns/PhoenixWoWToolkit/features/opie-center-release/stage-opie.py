"""Stage the hide-active adapter against exact private OPie 8.10.4 sources."""
import argparse
import hashlib
from pathlib import Path
import shutil

CORE = "OPieCore.lua"
BOOK = "Libs/ActionBook/ActionBook.lua"
EDITOR = "UI/Options/RingEdit.lua"
DIGESTS = {
    EDITOR: "55b477c45676c6e7ea2bba2b14f05b5c05370793b6761d05ec510db0dc02051f",
    CORE: "c636b8fdc2d93ddf7f5e3b1205db6746f00573391502d07fb1fb37917609c242",
    BOOK: "303059e3f3b158f46a6f415d563cd919fb4ab062ce6bbbe36a40c53eb4557f7f",
}


def replace_once(source, old, new):
    if source.count(old) != 1:
        raise ValueError(f"Expected one OPie patch anchor for {old!r}")
    return source.replace(old, new, 1)


def patch_book(book):
    book = replace_once(book, "\twipe(outCount) wipe(onStack)",
        "\tlocal hiddenAction, hiddenToken\n\twipe(outCount) wipe(onStack)")
    start = book.index("\t\t\tif (check1 == nil")
    end = book.index("\t\t\t\tlocal isCollection", start)
    book = book[:start] + """\t\t\tlocal actionVisible = (check1 == nil or KR:RunAttribute("EvaluateCmdOptions", check1) or "hide") ~= "hide"
\t\t\tlocal visibility = actionVisible and (check2 == nil or KR:RunAttribute("EvaluateCmdOptions", check2) or "hide")
\t\t\tif actionVisible and visibility == "hide-active" then
\t\t\t\tlocal mode = metadata["prMode-" .. tok] or 0
\t\t\t\tif i == 1 and not hiddenAction and not collections[aid] and mode % 4 == 1 then
\t\t\t\t\thiddenAction, hiddenToken = aid, tok
\t\t\t\tend
\t\t\telseif actionVisible and visibility ~= "hide" then
""" + book[end:]
    return replace_once(book, 'return ret, metadata["openAction-" .. root]',
        'return ret, metadata["openAction-" .. root], hiddenAction, hiddenToken')


def patch_core(core):
    core = replace_once(core, 'local firstFC, root, colData = nil, ..., AB:RunAttribute("GetCollectionContent", ...)',
        """local root = ...
\t\t\tlocal colData, _, hiddenAction, hiddenToken = AB:RunAttribute("GetCollectionContent", root)
\t\t\tlocal firstFC""")
    core = replace_once(core, "return collections[root][0], firstFC",
        "return collections[root][0], firstFC, hiddenAction, hiddenToken")
    core = replace_once(core, "local openAction, firstFC =",
        "local openAction, firstFC, hiddenAction, hiddenToken =")
    core = replace_once(core, "\t\t\tfastClickCA = fastClick and ring.CenterAction\n\n",
        """\t\t\tfastClickCA = fastClick and ring.CenterAction
\t\t\tif PhoenixHideActive and hiddenAction and not AI_NoPointer and openCause == "primary-binding" then
\t\t\t\tlocal centerIndex = -2
\t\t\t\tif openCollection == emptyTable then
\t\t\t\t\topenCollection, ctokens[cid] = newtable(), newtable()
\t\t\t\t\tcollections[cid] = openCollection
\t\t\t\tend
\t\t\t\topenCollection[centerIndex], ctokens[cid][centerIndex] = hiddenAction, hiddenToken
\t\t\t\tfastClick, fastClickCA = centerIndex, centerIndex
\t\t\t\tAIP_ActionFirstUp = AIP_ActionFirstUp or (AIP_Action ~= "use" and "useFC") or nil
\t\t\tend

""")
    core = replace_once(core, "local armMotionFC = fastClick and ring.MotionAction and true",
        "local armMotionFC = fastClick and fastClick > 0 and ring.MotionAction and true")
    core = replace_once(core, "if not openCollection[1] or AI_NoPointer then return nil end",
        "if (not openCollection[1] and fastClickCA ~= -2) or AI_NoPointer then return nil end")
    core = replace_once(core, "if radius > 2500 then", "if radius > 2500 and openCollection[1] then")
    core = replace_once(core, "if radius >= 40 then", "if radius >= 40 and openCollection[1] then")
    core = replace_once(core, "\t\t\tlocal pureToken =",
        """\t\t\tif pureSlice == -2 and interactionSource ~= "primary-binding" then
\t\t\t\treturn false
\t\t\tend
\t\t\tlocal pureToken =""")
    core = replace_once(core, "shouldUpdateFastClick and (activeRing.CenterAction",
        "pureSlice ~= -2 and shouldUpdateFastClick and (activeRing.CenterAction")
    core = replace_once(core, 'if button == "useFC" and not (isFC and slice) then',
        """if slice == -2 and (down or not isActiveRingTriggerClick) then
\t\t\t\t\treturn false
\t\t\t\tend
\t\t\t\tif button == "useFC" and not (isFC and slice) then""")
    core = replace_once(core, "if aidx then", "if aidx and aidx > 0 then")
    core = replace_once(core, 'ring.action, fastClick, fastSwitch and true, modLockState)',
        'ring.action, fastClick ~= -2 and fastClick or nil, fastSwitch and true, modLockState)')
    return replace_once(core, "\n-- Public API\n", """
-- Public API
function api:SetPhoenixHideActive(enabled)
\tif InCombatLockdown() then return false end
\tcoreEnvW.PhoenixHideActive = enabled == true
\treturn true
end
""")


def patch_editor(editor):
    return replace_once(editor, 'shTrim ~= "hide" and shTrim ~= "show"',
        'shTrim ~= "hide" and shTrim ~= "show" and shTrim ~= "hide-active"')


def stage(source, destination):
    if destination == source or source in destination.parents:
        raise ValueError("Use a separate destination outside the source add-on")
    patched = {}
    for name, patch in ((CORE, patch_core), (BOOK, patch_book), (EDITOR, patch_editor)):
        data = (source / name).read_bytes()
        if hashlib.sha256(data).hexdigest() != DIGESTS[name]:
            raise ValueError(f"{name} differs from the reviewed OPie 8.10.4 source")
        patched[name] = patch(data.decode("utf-8")).encode("utf-8")
    shutil.copytree(source, destination)
    for name, data in patched.items():
        (destination / name).write_bytes(data)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    try:
        stage(args.source.resolve(), args.destination.resolve())
    except (ValueError, OSError) as exc:
        parser.exit(1, str(exc) + "\n")

"""Build a private OPie 8.10.4 test copy from the operator's installed source."""
import argparse
import hashlib
from pathlib import Path
import shutil

CORE = "c636b8fdc2d93ddf7f5e3b1205db6746f00573391502d07fb1fb37917609c242"
VIEW = "c9fa518e33f6480fea27fb218f98c640cced5f90389213a984bc9c38fa974b91"


def verified_read(source, name, digest):
    data = (source / name).read_bytes()
    if hashlib.sha256(data).hexdigest() != digest:
        raise ValueError(f"{name} differs from the reviewed OPie 8.10.4 source")
    return data.decode("utf-8")


def replace_once(source, old, new):
    if source.count(old) != 1:
        raise ValueError(f"Expected one OPie patch anchor for {old!r}")
    return source.replace(old, new, 1)


def patch_core(core):
    core = replace_once(core, "\t\tprops.sortScope =",
        "\t\tprops.centerReleaseAction = newprops.centerReleaseAction\n\t\tprops.sortScope =")
    core = replace_once(core, "\tdata.LeftAction, data.LeftAction2 =",
        """\tdata.centerReleaseAction = props.centerReleaseAction
\tif data.centerReleaseAction then
\t\tdata.CenterAction, data.MotionAction = true, nil
\t\tdata.PrimaryAction, data.PrimaryActionUp, leftAction = "use", nil, nil
\t\tdata.NoPointer, rightAction = nil, "close"
\tend
\tdata.LeftAction, data.LeftAction2 =""")
    core = replace_once(core, "\t\t\tfastClickCA = fastClick and ring.CenterAction\n\n",
        """\t\t\tif ring.centerReleaseAction and openCause == "primary-binding" and #openCollection == 8 then
\t\t\t\tlocal centerIndex, token = -2, "PhoenixToolkitCenterReleaseTrialCenter"
\t\t\t\topenCollection[centerIndex] = ring.centerReleaseAction
\t\t\t\tctokens[cid][centerIndex], fcIgnore[token] = token, true
\t\t\t\tfastClick = centerIndex
\t\t\tend
\t\t\tfastClickCA = fastClick and ring.CenterAction

""")
    core = replace_once(core, "if button == \"useFC\" and not (isFC and slice) then",
        """if slice == -2 and (down or not isActiveRingTriggerClick) then
					return false
				end
				if button == "useFC" and not (isFC and slice) then""")
    core = replace_once(core, "\t\t\tlocal pureToken =",
        """\t\t\tif pureSlice == -2 and interactionSource ~= "primary-binding" then
\t\t\t\treturn false
\t\t\tend
\t\t\tlocal pureToken =""")
    core = replace_once(core, "\tif id < 1 or id > OR_ActiveSliceCount then return end",
        """\tif id == -2 then
\t\tlocal col = coreEnvW.collections[OR_ActiveCollectionID]
\t\tif col and col[id] then
\t\t\treturn coreEnvW.ctokens[OR_ActiveCollectionID][id], AB:GetSlotInfo(col[id], OR_ModifierLockState)
\t\tend
\t\treturn
\tend
\tif id < 1 or id > OR_ActiveSliceCount then return end""")
    return replace_once(core, "\n-- Public API\n", "\n-- Public API\napi.centerReleaseSlotVersion = 1\n")


def stage(source, destination):
    if destination == source or source in destination.parents:
        raise ValueError("Use a separate destination outside the source add-on")
    core = patch_core(verified_read(source, "OPieCore.lua", CORE))
    view = verified_read(source, "UI/RingView.lua", VIEW)
    view = replace_once(view, "if qaid and count > 0 then", "if qaid and qaid > 0 and count > 0 then")
    shutil.copytree(source, destination)
    (destination / "OPieCore.lua").write_bytes(core.encode("utf-8"))
    (destination / "UI/RingView.lua").write_bytes(view.encode("utf-8"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path, help="New directory for the private copy")
    args = parser.parse_args()
    try:
        stage(args.source.resolve(), args.destination.resolve())
    except (ValueError, OSError) as exc:
        parser.exit(1, f"{exc}\n")

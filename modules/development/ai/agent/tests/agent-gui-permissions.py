"""Characterize pinned bundle preference/default and resume decisions, without a GUI."""
import argparse
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

parser = argparse.ArgumentParser()
parser.add_argument("--source", type=Path, required=True, help="extracted pinned app.asar")
args = parser.parse_args()
spec = importlib.util.spec_from_file_location("patcher", Path(__file__).resolve().parents[1] / "gui-permissions.py")
patcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(patcher)
originals = {name: (args.source / name).read_text() for name in patcher.OWNERS}
initial = "webview/assets/app-initial-b7dae1c6de39.js"


def function(source, name, following):
    return source[source.index("function " + name + "("):source.index("function " + following + "(")]


with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    for name, source in originals.items():
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(source)
    patcher.patch(root)
    changed = (root / initial).read_text()
    # Execute actual unmodified reconciliation expressions from the pinned bundle.
    ce = "n!=null&&oe!=null&&(ae==null||ae.startsWith(`:`))&&(M!=null||pe!=null&&Sci(pe,P))&&oe!==_e"
    be = "b||Ce||ze||!I&&(L||ae==null&&oe!==`custom`)"
    assert ce in changed and be in changed
    script = "const assert=require('node:assert/strict');\n"
    script += function(changed, "Fci", "Ici") + function(changed, "Sci", "Cci")
    script += f"const reconcile=(pe,oe,ae)=>{{const n='chat',M=null,P=['auto','custom','read-only','full-access'],_e=pe,b=false,ze=false,I=false,L=false;const Ce={ce};return {{Ce,send:{be}}}}};"
    script += """
const native={'local':'auto'},snapshot=JSON.stringify(native),sandbox={};
assert.equal(Fci('local',sandbox,false,null,null,null),'custom');
const resumed=Fci('local',sandbox,false,null,'auto',':workspace');
assert.equal(resumed,'custom');
assert.deepEqual(reconcile(resumed,'auto',':workspace'),{Ce:true,send:true});
assert.equal(Fci('local',sandbox,false,null,'read-only',':read-only'),'read-only');
assert.deepEqual(reconcile('read-only','read-only',':read-only'),{Ce:false,send:false});
for(const saved of ['custom','auto','full-access']){
 const preferences={local:saved};
 assert.equal(Fci('local',preferences,false,null,'read-only',':read-only'),'read-only');
 assert.deepEqual(reconcile(Fci('local',preferences,false,null,'read-only',':read-only'),'read-only',':read-only'),{Ce:false,send:false});
 for(const profile of ['named-restricted',':unknown',':danger-full-access']){
  const picked=Fci('local',preferences,false,null,'auto',profile);
  assert.equal(picked,undefined);
  assert.equal(reconcile(picked,'auto',profile).Ce,false);
 }
 for(const mode of ['custom','granular','full-access','guardian-approvals']){
  assert.equal(Fci('local',preferences,false,null,mode,null),mode);
 }
 assert.equal(Fci('local',preferences,false,null,'unknown',null),undefined);
 assert.equal(Fci('local',preferences,false,null,'auto',':workspace'),saved);
}
for(const profile of ['named-restricted',':unknown',':danger-full-access']){
 assert.equal(Fci('local',sandbox,false,null,'auto',profile),undefined);
 assert.equal(reconcile(undefined,'auto',profile).Ce,false);
}
for(const mode of ['read-only','auto','custom','full-access']){
 sandbox.local=mode;
 assert.equal(Fci('local',sandbox,false,null,'auto',':workspace'),mode);
}
assert.equal(JSON.stringify(native),snapshot);
"""
    # Original Native resolver still reads its original map and honors Auto.
    script += function(originals[initial], "Fci", "Ici").replace("function Fci(", "function Native(")
    script += "assert.equal(Native('local',native,false,null),'auto');"
    subprocess.run([shutil.which("node"), "-e", script], check=True, capture_output=True, text=True)
    for name in originals:
        actual = (root / name).read_text()
        assert not any(key in actual for key in patcher.KEYS)
        for key in patcher.KEYS:
            assert actual.count(key.replace('`', '`phoenix-sandbox.', 1)) == originals[name].count(key)
    # Missing/duplicate/already-patched seams fail before writing any bundle.
    for invalid in [changed, originals[initial].replace(patcher.LOOKUP, "changed"),
                    originals[initial] + patcher.LOOKUP,
                    originals[initial].replace("updateThreadPermissions(n,Te(e))", "changed")]:
        for name, source in originals.items():
            (root / name).write_text(source)
        (root / initial).write_text(invalid)
        before = {name: (root / name).read_bytes() for name in originals}
        try:
            patcher.patch(root)
        except ValueError:
            pass
        else:
            raise AssertionError("Incompatible pinned bundle accepted")
        assert before == {name: (root / name).read_bytes() for name in originals}
print("agent-gui-permissions: pinned defaults, resume decisions, explicit selections and fail-closed seams passed")

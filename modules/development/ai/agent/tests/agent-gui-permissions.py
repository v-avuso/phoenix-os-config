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
    shared = originals["webview/assets/app-shared-f2257985f1b6.js"]
    # Actual decoder, Custom config mapper and outgoing request projection.
    # Equality is the only imported dependency used by the decoder; these probes
    # compare the string approval policy against the granular policy object.
    script += "const A_t={default:(a,b)=>JSON.stringify(a)===JSON.stringify(b)},kM={granular:{}};"
    for name, following in [("CM", "l_t"), ("u_t", "d_t"), ("d_t", "f_t"),
                            ("h_t", "g_t"), ("g_t", "__t"), ("C_t", "w_t"),
                            ("w_t", "OM"), ("OM", "T_t"), ("T_t", "E_t"), ("wM", "TM")]:
        script += function(shared, name, following)
    script += shared[shared.index("function k_t("):shared.index("var A_t,j_t,")]

    script += f"const reconcile=(pe,oe,ae)=>{{const n='chat',M=null,P=['auto','custom','read-only','full-access','guardian-approvals'],_e=pe,b=false,ze=false,I=false,L=false;const Ce={ce};return {{Ce,send:{be}}}}};"
    script += """
const native={'local':'auto'},snapshot=JSON.stringify(native),sandbox={};
assert.equal(Fci('local',sandbox,false,null,null,null),'custom');
const resumed=Fci('local',sandbox,false,null,'auto',':workspace');
assert.equal(resumed,'custom');
assert.deepEqual(reconcile(resumed,'auto',':workspace'),{Ce:true,send:true});
assert.equal(Fci('local',sandbox,false,null,'read-only',':read-only'),'read-only');
assert.deepEqual(reconcile('read-only','read-only',':read-only'),{Ce:false,send:false});
for(const saved of ['custom','auto','full-access','guardian-approvals']){
 const preferences={local:saved};
 assert.equal(Fci('local',preferences,false,null,'read-only',':read-only'),'read-only');
 assert.deepEqual(reconcile(Fci('local',preferences,false,null,'read-only',':read-only'),'read-only',':read-only'),{Ce:false,send:false});
 for(const profile of ['named-restricted',':unknown',':danger-full-access']){
  const picked=Fci('local',preferences,false,null,'auto',profile);
  assert.equal(picked,undefined);
  assert.equal(reconcile(picked,'auto',profile).Ce,false);
 }
 for(const mode of ['custom','granular','full-access']){
  assert.equal(Fci('local',preferences,false,null,mode,null),mode);
 }
 assert.equal(Fci('local',preferences,false,null,'unknown',null),undefined);
 assert.equal(Fci('local',preferences,false,null,'auto',':workspace'),saved);
 assert.equal(Fci('local',preferences,false,null,'guardian-approvals',':workspace'),saved);
}
for(const profile of ['named-restricted',':unknown',':danger-full-access']){
 assert.equal(Fci('local',sandbox,false,null,'auto',profile),undefined);
 assert.equal(reconcile(undefined,'auto',profile).Ce,false);
}
for(const mode of ['read-only','auto','custom','full-access','guardian-approvals']){
 sandbox.local=mode;
 assert.equal(Fci('local',sandbox,false,null,'auto',':workspace'),mode);
}
assert.equal(JSON.stringify(native),snapshot);
"""
    script += """
const ordinary={approvalPolicy:'on-request',approvalsReviewer:'auto_review',sandboxPolicy:{type:'workspaceWrite',writableRoots:['/workspace'],networkAccess:false,excludeSlashTmp:false,excludeTmpdirEnvVar:false}};
const decoded=d_t(ordinary);
assert.equal(decoded,'guardian-approvals'); // Actual Approve for me label's mode.
const selected=Fci('local',{},false,null,decoded,':workspace');
assert.equal(selected,'custom');
assert.deepEqual(reconcile(selected,decoded,':workspace'),{Ce:true,send:true});
const effective=OM(selected,['/workspace'],{sandbox_mode:'danger-full-access',approval_policy:'on-request',approvals_reviewer:'auto_review'});
assert.equal(effective.approvalPolicy,ordinary.approvalPolicy);
assert.equal(effective.approvalsReviewer,ordinary.approvalsReviewer);
assert.deepEqual(wM(effective),{sandboxPolicy:{type:'dangerFullAccess'}});
const restricted={...ordinary,sandboxPolicy:{type:'readOnly',networkAccess:false}};
assert.equal(d_t(restricted),'read-only');
assert.equal(Fci('local',{local:'custom'},false,null,d_t(restricted),':read-only'),'read-only');
assert.equal(Fci('local',{local:'custom'},false,null,decoded,'named-restricted'),undefined);
"""
    # Original Native resolver still reads its original map and honors Auto.
    script += function(originals[initial], "Fci", "Ici").replace("function Fci(", "function Native(")
    script += "assert.equal(Native('local',native,false,null),'auto');assert.equal(Native('local',{local:'guardian-approvals'},false,null),'guardian-approvals');"
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

"""Characterize pinned bundle preference/default and resume decisions, without a GUI."""
import argparse
import importlib.util
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

parser = argparse.ArgumentParser()
parser.add_argument("--source", type=Path, required=True, help="extracted pinned app.asar")
args = parser.parse_args()
spec = importlib.util.spec_from_file_location("patcher", Path(__file__).resolve().parents[1] / "gui-permissions.py")
patcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(patcher)
owners, initial = patcher.layout(args.source)
# An unsupported interpolated selection writer must not hide behind exact-key counts.
for unknown_owner, expression in [(False, "`permission-selection-by-host-id:${renamed}`"),
                                  (True, "`permission-selection-by-host-id:${renamed}`"),
                                  (False, '"permission-selection-by-host-id:"+renamed'),
                                  (True, '"permission-selection-by-host-id:"+renamed')]:
    with tempfile.TemporaryDirectory() as invalid_directory:
        invalid_root = Path(invalid_directory)
        for name in owners:
            target = invalid_root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text((args.source / name).read_text())
        target = invalid_root / ('webview/assets/unreviewed-writer.js' if unknown_owner else initial)
        with target.open('a') as output:
            output.write(';const extraWriter=' + expression + ';')
        before = {path: path.read_bytes() for path in invalid_root.rglob('*.js')}
        try:
            patcher.patch(invalid_root)
        except ValueError:
            pass
        else:
            raise AssertionError('Unsupported interpolated preference writer accepted')
        assert before == {path: path.read_bytes() for path in invalid_root.rglob('*.js')}

# Generated asset hashes and resolver identifiers are not semantic contracts.
with tempfile.TemporaryDirectory() as renamed_directory:
    renamed_root = Path(renamed_directory)
    for name in owners:
        source = (args.source / name).read_text()
        target = renamed_root / (name.rsplit('-', 1)[0] + '-renamed.js')
        target.parent.mkdir(parents=True, exist_ok=True)
        if name == initial:
            lookup, _, call, _ = patcher.resolver(source)
            symbol = lookup.split('(', 1)[0].removeprefix('function ')
            source = source.replace('function ' + symbol + '(', 'function renamedResolver(').replace(
                call, call.replace(symbol + '(', 'renamedResolver('))
        target.write_text(source)
    patcher.patch(renamed_root)
    actual = (renamed_root / (initial.rsplit('-', 1)[0] + '-renamed.js')).read_text()
    assert 'function renamedResolver(' in actual and 'mode,profile)' in actual
    assert 'return`custom`}' in actual
    for path in renamed_root.rglob('*.js'):
        assert not any(key in path.read_text() for key in patcher.KEYS)

if patcher.resolver((args.source / initial).read_text())[3]:
    originals = {name: (args.source / name).read_text() for name in owners}
    lookup, _, call, _ = patcher.resolver(originals[initial])
    symbol = lookup.split('(', 1)[0].removeprefix('function ')
    current = call.startswith('xe=')
    seams = patcher.CURRENT_SEAMS if current else patcher.NEW_SEAMS
    # Normalize only this fixture's explicitly reviewed generated identifiers.
    # Production matching still requires the exact resolver, call and seams.
    helpers = dict(zip(
        ['EJ','e4e','t4e','s4e','c4e','DJ','OJ','h4e','g4e','kJ','_4e','n4e','AJ','b4e','a4e'],
        ['zH','Q7e','$7e','a9e','o9e','BH','VH','p9e','m9e','HH','h9e','e9e','UH','v9e','r9e'])) if current else {}
    canonical = {value: key for key, value in helpers.items()}
    if current:
        canonical.update({'WH':'jJ', 'GH':'MJ', 'T9e':'D4e', 'b9e':'S4e'})
    def normalize(text, names):
        return re.sub(r'[A-Za-z_$][\w$]*', lambda match: names.get(match[0], match[0]), text)
    def extract(source, name):
        start = source.index('function ' + name + '(')
        end = source.find('function ', start + 9)
        return source[start:end].split('}var ',1)[0] + ('}' if '}var ' in source[start:end] else '')
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        for name, source in originals.items():
            target = root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(source)
        patcher.patch(root)
        changed = (root / initial).read_text()
        assert call[:-1] + ',se,oe)' in changed
        for seam in seams:
            assert seam in changed
        script = "const assert=require('node:assert/strict');"
        script += extract(changed, symbol).replace('function ' + symbol + '(', 'function rSo(')
        script += extract(originals[initial], symbol).replace('function ' + symbol + '(', 'function Native(')
        shared = originals[next(name for name in owners if '/app-shared-' in name)]
        for name in ['EJ','e4e','t4e','s4e','c4e','DJ','OJ','h4e','g4e','kJ','_4e','n4e','AJ','b4e','a4e']:
            script += normalize(extract(shared, helpers.get(name, name)), canonical)
        script += "const jJ={default:(a,b)=>JSON.stringify(a)===JSON.stringify(b)},MJ={granular:{}},D4e={type:'readOnly',networkAccess:false},S4e='guardian_approval';"
        script += """
const modes=['read-only','auto','custom','full-access','guardian-approvals','granular'];
assert.equal(rSo('local',{}, {},false,null,null,null),'custom');
// Matching config-derived entries are not deliberate choices, per upstream.
assert.equal(Native('local',{local:'auto'},{local:'auto'},false,null),undefined);
assert.equal(rSo('local',{local:'auto'},{local:'auto'},false,null,'auto',':workspace'),'custom');
assert.equal(rSo('local',{durable:'guardian-approvals'},{},true,'durable','auto',':workspace'),'guardian-approvals');
assert.equal(rSo('local',{durable:'guardian-approvals'},{durable:'guardian-approvals'},true,'durable','auto',':workspace'),'custom');
for(const saved of modes){
 const preferences={local:saved};
 assert.equal(rSo('local',preferences,{},false,null,'read-only',':read-only'),'read-only');
 for(const profile of ['named-restricted',':unknown',':danger-full-access']){
  assert.equal(rSo('local',preferences,{},false,null,'auto',profile),undefined);
 }
 for(const mode of ['custom','granular','full-access','read-only']){
  assert.equal(rSo('local',preferences,{},false,null,mode,null),mode);
 }
 assert.equal(rSo('local',preferences,{},false,null,'unknown',null),undefined);
 assert.equal(rSo('local',preferences,{},false,null,'auto',':workspace'),saved);
}
const reconcile=(be,se,oe)=>{
 const n='chat',N=modes,Te=be,b=false,we=false,qe=false,F=false,I=false,ne=null,ce={type:'workspaceWrite'};
 const je=JE_EXPRESSION;
 return {reconcile:je,profile:PROFILE_EXPRESSION,send:SEND_EXPRESSION};
};
assert.deepEqual(reconcile('custom','guardian-approvals',':workspace'),{reconcile:true,profile:null,send:true});
assert.deepEqual(reconcile('read-only','read-only',':read-only'),{reconcile:false,profile:':read-only',send:false});
for(const profile of ['named-restricted',':unknown',':danger-full-access']){
 assert.equal(reconcile(undefined,'auto',profile).reconcile,false);
}
const ordinary={approvalPolicy:'on-request',approvalsReviewer:'auto_review',sandboxPolicy:{type:'workspaceWrite',writableRoots:['/workspace'],networkAccess:false,excludeSlashTmp:false,excludeTmpdirEnvVar:false}};
assert.equal(t4e(ordinary),'guardian-approvals');
const selected=rSo('local',{}, {},false,null,t4e(ordinary),':workspace');
assert.equal(selected,'custom');
const effective=kJ(selected,['/workspace'],{sandbox_mode:'danger-full-access',approval_policy:'on-request',approvals_reviewer:'auto_review'});
assert.equal(effective.approvalsReviewer,'auto_review');
assert.deepEqual(a4e(effective),{sandboxPolicy:{type:'dangerFullAccess'}});
assert.equal(t4e({...ordinary,sandboxPolicy:{type:'readOnly',networkAccess:false}}),'read-only');
"""
        locals_map = {'xe':'be','P':'N','Ee':'Te','Te':'we','Me':'je','L':'I','I':'F','Je':'qe'} if current else {}
        script = script.replace('JE_EXPRESSION',normalize(seams[0].split('=',1)[1], locals_map)).replace('PROFILE_EXPRESSION',normalize(seams[1].split('=',1)[1], locals_map)).replace('SEND_EXPRESSION',normalize(seams[2].split('=',1)[1], locals_map))
        subprocess.run([shutil.which('node'),'-e',script],check=True,capture_output=True,text=True)
        for name, source in originals.items():
            actual = (root/name).read_text()
            assert not any(key in actual for key in patcher.KEYS)
            for key in patcher.KEYS:
                assert actual.count(key.replace('`','`phoenix-sandbox.',1)) == source.count(key)
        for invalid in [changed, originals[initial].replace(lookup,'changed'),
                        originals[initial]+lookup,
                        originals[initial].replace(call,'changed'),
                        originals[initial]+call,
                        originals[initial]+(patcher.NEW_CALL if current else patcher.CURRENT_CALL).replace('rSo(',symbol+'('),
                        *(originals[initial].replace(seam,'changed') for seam in seams),
                        *(originals[initial]+seam for seam in seams)]:
            for name, source in originals.items():
                (root/name).write_text(source)
            (root/initial).write_text(invalid)
            before={name:(root/name).read_bytes() for name in originals}
            try:
                patcher.patch(root)
            except ValueError:
                pass
            else:
                raise AssertionError('Incompatible updated bundle accepted')
            assert before=={name:(root/name).read_bytes() for name in originals}
    print('agent-gui-permissions: updated defaults, config-derived preferences, restrictive resume and isolated writers passed')
    raise SystemExit(0)

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

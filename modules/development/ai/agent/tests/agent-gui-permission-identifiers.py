"""Renaming must preserve permission bindings; semantic changes must fail closed."""
import argparse
import importlib.util
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('patcher', Path(__file__).resolve().parents[1] / 'gui-permissions.py')
patcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(patcher)


def rename(source, names):
    # These fixtures rename identifiers only, never strings or property names.
    return re.sub(r'`[^`]*`|[A-Za-z_$][\w$]*',
                  lambda m: names.get(m[0], m[0]), source)


def fixture():
    return ';'.join((patcher.NEW_LOOKUP, patcher.LATEST_CALL, *patcher.LATEST_SEAMS))


def bundle(root, source):
    for name, counts in patcher.OWNERS.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        keys = ';'.join(key for key, count in zip(patcher.KEYS, counts) for _ in range(count))
        path.write_text(keys + ';' + (source if '/app-initial-' in name else ''))


class Identifiers(unittest.TestCase):
    def test_consistent_caller_renaming(self):
        # Rename every caller role, including the mode/profile passed to our guard.
        tokens = set(re.findall(r'[A-Za-z_$][\w$]*', patcher.LATEST_CALL + ''.join(patcher.LATEST_SEAMS)))
        fixed = {'null', 'if', 'return', 'startsWith', 'includes', 'type', 'isSet',
                 'updateThreadPermissions', 'threadApprovalsReviewer', 'threadPermissionProfileId',
                 'threadMode', 'threadSandboxPolicy', 'permissionOverrideThreadSettings',
                 'permissionProfileId', 'shouldSendPermissionOverrides', 'custom', 'dangerFullAccess'}
        names = {token: '$renamed' + str(i) for i, token in enumerate(sorted(tokens - fixed))}
        source = patcher.NEW_LOOKUP.replace('rSo', names['rSo']) + ';' + rename(
            ';'.join((patcher.LATEST_CALL, *patcher.LATEST_SEAMS)), names)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle(root, source)
            patcher.patch(root)
            changed = (root / next(n for n in patcher.OWNERS if '/app-initial-' in n)).read_text()
            self.assertIn(rename(patcher.LATEST_CALL, names)[:-1] + ',' + names['le'] + ',' + names['ce'] + ')', changed)

    def test_all_reviewed_variants(self):
        for call, (seams, _) in patcher.RECONCILIATION.items():
            with self.subTest(call=call):
                patcher.resolver(';'.join((patcher.NEW_LOOKUP, call, *seams)))

    def test_invalid_logic_bindings_and_ambiguity_leave_bundle_untouched(self):
        source = fixture()
        for invalid in (
            source.replace('le!==ke', 'le===ke'),
            source.replace('le!==ke', 'ce!==ke'),
            source.replace('permissionProfileId:ce', 'permissionProfileId:le'),
            source.replace('`dangerFullAccess`', '`workspaceWrite`'),
            source.replace('.startsWith', '.endsWith'),
            source.replace('Ce=rSo(i,z,ee,ge,c)', 'Ce=rSo(i,z,z,ge,c)'),
            source + ';' + patcher.LATEST_CALL,
            source + ';' + patcher.LATEST_SEAMS[0],
            source + ';' + patcher.NEW_LOOKUP,
        ):
            with self.subTest(invalid=invalid), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                bundle(root, invalid)
                before = {p: p.read_bytes() for p in root.rglob('*.js')}
                with self.assertRaises(ValueError):
                    patcher.patch(root)
                self.assertEqual(before, {p: p.read_bytes() for p in before})


def actual_bundle(source):
    """Run the real patch and guarded resolver from an extracted publisher bundle."""
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        shutil.copytree(source, root, dirs_exist_ok=True)
        _, initial = patcher.layout(root)
        original = (root / initial).read_text()
        lookup, replacement, call, _ = patcher.resolver(original)
        patcher.patch(root)
        changed = (root / initial).read_text()
        assert replacement in changed and lookup not in changed
        name = lookup.split('(', 1)[0].removeprefix('function ')
        script = "const assert=require('node:assert/strict');" + replacement
        script += f"""
for(const saved of ['auto','custom','full-access','guardian-approvals','granular','read-only']){{
 for(const profile of ['named-restricted',':unknown',':danger-full-access']){{
  assert.equal({name}('local',{{local:saved}},{{}},false,null,'auto',profile),undefined);
 }}
 assert.equal({name}('local',{{local:saved}},{{}},false,null,'read-only',':read-only'),'read-only');
 assert.equal({name}('local',{{local:saved}},{{}},false,null,'custom',':workspace'),'custom');
}}
assert.equal({name}('local',{{}},{{}},false,null,'auto',':workspace'),'custom');
"""
        subprocess.run(['node', '-e', script], check=True)
        # Execute the actual reconciliation expressions and restricted resume
        # result, not just our resolver. These probes target inherited-default
        # bundles (the installed reference and the previously failed update).
        bindings = {'rSo': name}
        actual = []
        for template in (patcher.LATEST_CALL, *patcher.LATEST_SEAMS):
            matched, bindings = patcher.fragment(original, template, bindings)
            actual.append(matched)
        reverse = {value: key for key, value in bindings.items()}
        normalized = [rename(part, reverse) for part in actual[1:]]
        start = original.index(actual[5])
        early = original[start:original.index('};', start)]
        fields = []
        for key in ('agentMode', 'permissionProfileId', 'shouldSendPermissionOverrides',
                    'permissionOverrideThreadSettings'):
            value = re.search(r'\b' + key + r':([^,}]+)', early)[1]
            fields.append(key + ':' + rename(value, reverse))
        script = "const assert=require('node:assert/strict');" + replacement.replace(name + '(', 'rSo(')
        script += """
const resumed=(saved,le,ce)=>{
 const n='chat',i='local',Ce=rSo(i,{local:saved},{},false,null,le,ce),
       S=false,Oe=false,je=true,Me=false,Ze=false,zS=()=>false,
       Le=()=>{throw Error('Unexpected permission override')};
 if(CONDITION)return {FIELDS};
 return {fallthrough:true};
};
for(const saved of ['auto','full-access','custom','guardian-approvals']){
 for(const profile of ['named-restricted',':unknown',':danger-full-access']){
  assert.deepEqual(resumed(saved,'auto',profile),{agentMode:'auto',permissionProfileId:profile,
    shouldSendPermissionOverrides:false,permissionOverrideThreadSettings:null});
 }
}
assert.deepEqual(resumed('full-access','auto',':workspace'),{fallthrough:true});
const newChat=(inherit,profile,modelRequired=false)=>{
 const n=null,le=null,ce=null,Ce='custom',F=['custom'],ke='custom',S=modelRequired,Oe=false,
       R=true,ie=profile,Ze=false,L=false,o=inherit,I=false,re={isSet:false},ue=null;
 const INHERIT;
 const RECONCILE;
 return {profile:PROFILE,send:SEND};
};
assert.deepEqual(newChat(true,null),{profile:null,send:false});
assert.deepEqual(newChat(false,null),{profile:null,send:true});
assert.deepEqual(newChat(false,'named-restricted'),{profile:'named-restricted',send:true});
assert.deepEqual(newChat(false,'named-restricted',true),{profile:null,send:true});
""".replace('CONDITION', normalized[4].removeprefix('if(').removesuffix(')return')).replace(
            'FIELDS', ','.join(fields)).replace('INHERIT', normalized[6]).replace(
            'RECONCILE', normalized[0]).replace('PROFILE', normalized[1].split('=', 1)[1]).replace(
            'SEND', normalized[2].split('=', 1)[1])
        subprocess.run(['node', '-e', script], check=True)
        print('Actual bundle: renaming, restrictive resume, outgoing permissions and inherited defaults passed')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path)
    args, remaining = parser.parse_known_args()
    result = unittest.main(argv=[__file__, *remaining], exit=False).result
    if not result.wasSuccessful():
        sys.exit(1)
    if args.source:
        actual_bundle(args.source)

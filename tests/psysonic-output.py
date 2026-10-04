#!/usr/bin/env python3
"""Apply the exact patch to pinned sources; exercise only synthetic device state.

Usage: python3 tests/psysonic-output.py UPSTREAM_SOURCE
Requires patch, rustc and Node 24 on PATH. Never accesses the live app profile.
"""
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

repo = Path(__file__).resolve().parents[1]
source = Path(sys.argv[1])
paths = [
    'src-tauri/crates/psysonic-audio/src/dev_io.rs',
    'src-tauri/crates/psysonic-audio/src/engine/output_stream.rs',
    'src/features/playback/store/audioListenerSetup/initialAudioSync.ts',
]
with tempfile.TemporaryDirectory(prefix='psysonic-output-') as tmp:
    tree = Path(tmp)
    for name in paths:
        target = tree / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source / name, target)
    subprocess.run(['patch', '--batch', '--fuzz=0', '-p1', '-i',
                    str(repo / 'patches/psysonic-safe-output.patch')], cwd=tree, check=True)
    dev = (tree / paths[0]).read_text()
    predicate = re.search(r'pub\(crate\) fn is_silent_alsa_pcm\(.*?\n\}', dev, re.S).group()
    fixture = tree / 'device.rs'
    fixture.write_text(predicate + '''
fn main() {
    assert!(is_silent_alsa_pcm(Some("null")));
    for driver in [None, Some("pipewire"), Some("pulse"), Some("default"),
                   Some("hw:0,0"), Some("nullish")] {
        assert!(!is_silent_alsa_pcm(driver));
    }
}
''')
    subprocess.run(['rustc', str(fixture), '-o', str(tree / 'device')], check=True)
    subprocess.run([str(tree / 'device')], check=True)
    output = (tree / paths[1]).read_text()
    # Guard must precede all configuration queries and stream construction.
    assert output.index('is_silent_alsa_pcm') < output.index('let (config, choice)')
    sync = (tree / paths[2]).read_text()
    recovery = sync[sync.index('  if (audioOutputDevice) {'):sync.rindex('\n}')]
    js = tree / 'startup.cjs'
    js.write_text('''const assert = require('node:assert/strict');
const tick = () => new Promise(resolve => setImmediate(resolve));
const recover = new Function('audioOutputDevice', 'audioSetDevice', 'useAuthStore',
''' + repr(recovery) + ''');
async function scenario(pin, behavior) {
  let state = {audioOutputDevice: pin, other: 'preserve'};
  let calls = [];
  let writes = [];
  const store = {getState: () => ({...state, setAudioOutputDevice(value) {
    writes.push(value); state.audioOutputDevice = value;
  }})};
  const set = async args => {
    calls.push(args.deviceName);
    if (behavior === 'concurrent' && args.deviceName === pin) {
      state.audioOutputDevice = 'new-choice'; throw Error('unavailable');
    }
    if (args.deviceName !== null && behavior !== 'valid') throw Error('unavailable');
    if (args.deviceName === null && behavior === 'no-output') throw Error('offline');
  };
  recover(pin, set, store);
  await tick(); await tick();
  assert.equal(state.other, 'preserve');
  return {state, calls, writes};
}
(async () => {
  let r = await scenario('missing', 'missing');
  assert.deepEqual(r.calls, ['missing', null]);
  assert.deepEqual(r.writes, [null]);
  assert.equal(r.state.audioOutputDevice, null);
  r = await scenario('working', 'valid');
  assert.deepEqual(r.calls, ['working']); assert.deepEqual(r.writes, []);
  r = await scenario('missing', 'no-output');
  assert.deepEqual(r.calls, ['missing', null]); assert.deepEqual(r.writes, []);
  r = await scenario('missing', 'concurrent');
  assert.deepEqual(r.calls, ['missing']); assert.equal(r.state.audioOutputDevice, 'new-choice');
  r = await scenario(null, 'valid');
  assert.deepEqual(r.calls, []); assert.deepEqual(r.writes, []);
})().catch(error => {console.error(error); process.exitCode = 1;});
''')
    subprocess.run(['node', str(js)], check=True)
print('PASS: silent PCM guard; saved missing/valid/no-output/concurrent/default recovery')

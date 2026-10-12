#!/usr/bin/env python3
"""Guard the audited upstream call graph; never connect to the compositor."""
import pathlib
import re
import sys

source = pathlib.Path(sys.argv[1])
restore = (source / 'src/core/restore.rs').read_text().split('#[cfg(test)]\nmod tests {')[0]


def section(start, end):
    assert restore.count(start) == 1, start
    return restore.split(start, 1)[1].split(end, 1)[0]


# Simple restore passes no layout role. Only a layout role reaches the sole
# closewindow dispatcher (splash superseding); late simple windows have no role.
simple = section('async fn restore_simple(', 'async fn restore_with_layout(')
assert simple.count('.restore_window(') == 1
assert simple.count('MasterRole::None,') == 1
assert '.restore_simple(' in restore.split('if self.restore_layout {', 1)[1].split('if had_focus_on_activate {', 1)[0].split('} else {', 1)[1]
launch = section('async fn launch_and_track(', 'async fn restore_window(')
assert re.search(r'if master_role == MasterRole::None\s*\{\s*addr.clone\(\)\s*\}\s*else\s*\{\s*self.resolve_splash_supersede', launch)
assert re.search(r'placement: if master_role == MasterRole::Promote\s*\{\s*PlacementHint::MasterPromote\s*\}\s*else\s*\{\s*PlacementHint::None', launch)
assert restore.count('"closewindow ') == 1
splash = section('async fn resolve_splash_supersede(', 'async fn apply_split_ratios(')
assert '"closewindow ' in splash
window = section('async fn restore_window(', 'async fn wait_for_open_event(')
assert '.launch_and_track(' in window
assert 'master_role,' in window
for body in (simple, launch, window):
    assert not re.search(r'\b(?:kill|closewindow|retile_superseding_window|restore_with_layout|restore_dwindle|restore_master)\b', body)
assert not re.search(r'Command::new|libc::kill|"(?:killactive|exit|exec .*kill)\b', restore)
# Actual upstream Lua conversion handles exec + explicit workspace/geometry;
# no alternative shell session manager or compositor subprocess is introduced.
lua = (source / 'src/ipc/lua_compat.rs').read_text()
for dispatcher in ('exec', 'movetoworkspacesilent', 'setfloating', 'resizewindowpixel', 'movewindowpixel'):
    assert f'"{dispatcher}"' in lua, dispatcher
print('hypr-persist audited simple restore source guards passed')

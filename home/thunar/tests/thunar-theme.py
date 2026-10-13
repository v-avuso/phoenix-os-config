#!/usr/bin/env python3
"""Render the actual patched CLI functions into a fixture-owned directory.

Arguments: patched Caelestia source root, output directory. No dconf/session calls.
"""
import ast
from pathlib import Path
import sys
from types import SimpleNamespace

source, target = map(Path, sys.argv[1:])
module = ast.parse((source / 'src/caelestia/utils/theme.py').read_text())
functions = [node for node in module.body if isinstance(node, ast.FunctionDef) and node.name in {'gen_replace', 'apply_gtk'}]
assert len(functions) == 2
for node in functions:
    node.decorator_list = []
calls = []
namespace = {'Path': Path, 'subprocess': SimpleNamespace(run=lambda argv: calls.append(argv)),
             'templates_dir': source / 'src/caelestia/data/templates',
             'sync_papirus_colors': lambda _: None}

def atomic_write(path, contents):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.fixture-new')
    temporary.write_text(contents)
    temporary.replace(path)

namespace['atomic_write'] = atomic_write
exec(compile(ast.Module(body=functions, type_ignores=[]), 'patched-theme.py', 'exec'), namespace)
for mode in ['light', 'dark']:
    colours = {'primary': '123456' if mode == 'light' else 'aabbcc',
               'onPrimary': 'ffffff' if mode == 'light' else '000000',
               'surface': 'fafafa' if mode == 'light' else '101010',
               'background': 'eeeeee' if mode == 'light' else '202020',
               'onBackground': '000000' if mode == 'light' else 'ffffff',
               'surfaceDim': 'dddddd' if mode == 'light' else '303030',
               'onSurface': '000000' if mode == 'light' else 'ffffff',
               'surfaceContainerLow': 'e0e0e0' if mode == 'light' else '404040'}
    namespace['config_dir'] = target / mode
    namespace['apply_gtk'](colours, mode)
    name = 'adw-gtk3-dark' if mode == 'dark' else 'adw-gtk3'
    assert ['dconf', 'write', '/org/gnome/desktop/interface/gtk-theme', repr(name)] in calls
    assert ['dconf', 'write', '/org/gnome/desktop/interface/color-scheme', repr('prefer-' + mode)] in calls
    for gtk in ['gtk-3.0', 'gtk-4.0']:
        css = (target / mode / gtk / 'gtk.css').read_text()
        assert '{{' not in css and '@primary' not in css
        assert '@define-color theme_selected_fg_color @accent_fg_color;' in css
        assert '{{' not in (target / mode / gtk / 'thunar.css').read_text()
print('Patched Caelestia: both modes, GTK3/4 and palette selection names verified')

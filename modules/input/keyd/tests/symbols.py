"""Check actual keyd declarations against the system XKB Compose engine.

Usage: python3 symbols.py /path/libxkbcommon.so /path/en_US.UTF-8/Compose /path/keyd /path/share/X11/xkb
No input events are injected into the live desktop.
"""
import ctypes as c
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

root = Path(__file__).resolve().parents[4]
module = json.loads(subprocess.check_output([
    'nix-instantiate', '--eval', '--strict', '--json', '--expr',
    f'(import {root}/modules/input/keyd/default.nix {{}})',
]))
settings = module['services']['keyd']['keyboards']['default']['settings']
os.environ['XKB_CONFIG_ROOT'] = sys.argv[4]
xkb = c.CDLL(sys.argv[1])

def bind(name, result, *args):
    fn = getattr(xkb, name)
    fn.restype, fn.argtypes = result, list(args)
    return fn

context = bind('xkb_context_new', c.c_void_p, c.c_int)(0)
new_table = bind('xkb_compose_table_new_from_buffer', c.c_void_p,
                 c.c_void_p, c.c_char_p, c.c_size_t, c.c_char_p, c.c_int, c.c_int)
data = Path(sys.argv[2]).read_bytes()
table = new_table(context, data, len(data), b'en_US.UTF-8', 1, 0)
assert table, 'Could not load standard Compose table'
state = bind('xkb_compose_state_new', c.c_void_p, c.c_void_p, c.c_int)(table, 0)
feed = bind('xkb_compose_state_feed', c.c_int, c.c_void_p, c.c_uint)
status = bind('xkb_compose_state_get_status', c.c_int, c.c_void_p)
utf8 = bind('xkb_compose_state_get_utf8', c.c_int, c.c_void_p, c.c_char_p, c.c_size_t)
reset = bind('xkb_compose_state_reset', None, c.c_void_p)
class Names(c.Structure):
    _fields_ = [(name, c.c_char_p) for name in ('rules', 'model', 'layout', 'variant', 'options')]

names = Names(b'evdev', b'pc105', b'us', b'', module['services']['xserver']['xkb']['options'].encode())
keymap = bind('xkb_keymap_new_from_names', c.c_void_p, c.c_void_p, c.POINTER(Names), c.c_int)(context, c.byref(names), 0)
assert keymap, 'Could not load US keymap'
get_syms = bind('xkb_keymap_key_get_syms_by_level', c.c_int, c.c_void_p,
                c.c_uint, c.c_uint, c.c_uint, c.POINTER(c.POINTER(c.c_uint)))
# Linux evdev codes; XKB uses an offset of eight.
codes = {'compose': 127, 'apostrophe': 40, 'dot': 52, '6': 7,
         'a': 30, 'o': 24, 'u': 22, 's': 31, 'e': 18, 'equal': 13, 'minus': 12}

def token_sym(token):
    shifted = token.startswith('S-')
    key = token[2:] if shifted else token
    syms = c.POINTER(c.c_uint)()
    assert get_syms(keymap, codes[key] + 8, 0, int(shifted), c.byref(syms)) == 1
    return syms[0]

expected = {
    'symbols': dict(a='ä', o='ö', u='ü', s='ß', e='€', **{'-': '–', 'grave': '^'}),
    'symbols+shift': dict(a='Ä', o='Ö', u='Ü'),
}
for layer, outputs in expected.items():
    assert set(settings[layer]) == set(outputs), f'Unexpected bindings in {layer}'
    for key, wanted in outputs.items():
        macro = settings[layer][key]
        assert macro.startswith('macro(') and macro.endswith(')'), (layer, key, macro)
        tokens = macro[6:-1].split()
        reset(state)
        symbols = [token_sym(t) for t in tokens]
        if symbols == [0x5e]:
            actual = '^'
        else:
            for symbol in symbols:
                assert feed(state, symbol) == 1
            assert status(state) == 2, (layer, key, macro, 'did not compose')
            buf = c.create_string_buffer(32)
            utf8(state, buf, len(buf))
            actual = buf.value.decode()
        assert actual == wanted, (layer, key, actual, wanted)
assert settings['main']['capslock'] == 'layer(symbols)'
with tempfile.TemporaryDirectory() as tmp:
    config = Path(tmp) / 'default.conf'
    config.write_text('[ids]\n*\n\n' + '\n'.join(
        f'[{layer}]\n' + '\n'.join(f'{key}={value}' for key, value in bindings.items())
        for layer, bindings in settings.items()))
    subprocess.run([sys.argv[3], 'check', str(config)], check=True)
print('PASS: all 10 Caps bindings produce expected symbols; keyd accepts configuration')

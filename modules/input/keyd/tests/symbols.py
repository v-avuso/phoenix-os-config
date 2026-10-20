"""Check actual keyd input/output events through a real XKB keyboard state.

Invoked by symbols.nix; no live keyboard events or application input are used.
"""
import ctypes as c
import json
from pathlib import Path
import subprocess
import sys
import tempfile

module = json.loads(Path(sys.argv[1]).read_text())
settings = module['settings']
xkb = c.CDLL(sys.argv[2])


def bind(name, result, *args):
    fn = getattr(xkb, name)
    fn.restype, fn.argtypes = result, list(args)
    return fn


class Names(c.Structure):
    _fields_ = [(name, c.c_char_p) for name in ('rules', 'model', 'layout', 'variant', 'options')]


context = bind('xkb_context_new', c.c_void_p, c.c_int)(0)
names = Names(b'evdev', b'pc105', *(module['xkb'][name].encode() for name in ('layout', 'variant', 'options')))
keymap = bind('xkb_keymap_new_from_names', c.c_void_p, c.c_void_p, c.POINTER(Names), c.c_int)(context, c.byref(names), 0)
assert keymap, 'Could not load configured keymap'
new_state = bind('xkb_state_new', c.c_void_p, c.c_void_p)
update = bind('xkb_state_update_key', c.c_int, c.c_void_p, c.c_uint, c.c_int)
utf8 = bind('xkb_state_key_get_utf8', c.c_int, c.c_void_p, c.c_uint, c.c_char_p, c.c_size_t)
unref = bind('xkb_state_unref', None, c.c_void_p)
codes = {'capslock': 58, 'shift': 42, 'a': 30, 'o': 24, 'u': 22, 's': 31,
         'e': 18, '-': 12, 'grave': 41, 'apostrophe': 40, '6': 7, 'b': 48}
expected = {
    'symbols': dict(a='ä', o='ö', u='ü', s='ß', e='€', **{'-': '–', 'grave': '^'}),
    'symbols+shift': dict(a='Ä', o='Ö', u='Ü'),
}


def check(config, keys, wanted):
    events = '\n'.join(f'{codes[key]} {down} {10 + i * 20}' for i, (key, down) in enumerate(keys))
    output = subprocess.check_output([sys.argv[3], str(config)], input=events, text=True)
    state = new_state(keymap)
    actual = ''
    held = set()
    try:
        for line in output.splitlines():
            code, down = map(int, line.split())
            assert (code in held) != bool(down), ('Unbalanced key event', code, down)
            if down:
                held.add(code)
            else:
                held.remove(code)
            update(state, code + 8, down)
            if down:
                buf = c.create_string_buffer(32)
                utf8(state, code + 8, buf, len(buf))
                actual += buf.value.decode()
        assert not held, ('Keys left held', held)
        assert actual == wanted, (keys, actual, wanted)
    finally:
        unref(state)


with tempfile.TemporaryDirectory() as tmp:
    config = Path(tmp) / 'default.conf'
    config.write_text('[ids]\n*\n\n' + '\n'.join(
        f'[{layer}]\n' + '\n'.join(f'{key}={value}' for key, value in bindings.items())
        for layer, bindings in settings.items()))
    count = 0
    for layer, outputs in expected.items():
        assert set(settings[layer]) == set(outputs), f'Unexpected bindings in {layer}'
        for key, wanted in outputs.items():
            modifiers = ['capslock'] + (['shift'] if '+' in layer else [])
            for order in [modifiers, list(reversed(modifiers))] if '+' in layer else [modifiers]:
                keys = [(m, 1) for m in order] + [(key, 1), (key, 0)] + [(m, 0) for m in reversed(order)]
                # Include ordinary text afterward to detect leaked modifiers/dead keys.
                check(config, keys + [('b', 1), ('b', 0)], wanted + 'b')
                count += 1
    keys = [('capslock', 1)]
    for key in expected['symbols']:
        keys += [(key, 1), (key, 0)]
    check(config, keys + [('capslock', 0)], ''.join(expected['symbols'].values()))
    check(config, [('capslock', 1), ('capslock', 0)], '')
    # Preserve the ordinary US base and shifted punctuation, without dead keys.
    for key, wanted in [('a', 'a'), ('apostrophe', "'"), ('grave', '`'), ('-', '-')]:
        check(config, [(key, 1), (key, 0)], wanted)
    for key, wanted in [('a', 'A'), ('apostrophe', '"'), ('6', '^')]:
        check(config, [('shift', 1), (key, 1), (key, 0), ('shift', 0)], wanted)
print(f'PASS: {count} symbol/order cases, consecutive symbols, Caps alone and US baseline; no extra text or held keys')

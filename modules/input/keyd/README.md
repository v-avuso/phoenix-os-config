# Caps symbol layer

## Intentions

- Hold Caps Lock to type German letters and common symbols on the US desktop
  layout; Caps Lock itself never toggles capitalization.
- Resolve each symbol with one keyboard chord, without application-dependent
  Compose sequences, clipboard access or per-application remapping.

`../../default.nix` imports this module. It selects xkeyboard-config's maintained
`us(altgr-weur)` variant, whose ordinary letters and punctuation retain US typing.
Its third/fourth levels contain every required symbol. keyd emits single AltGr
chords for those levels, and Shift+6 for the caret. Physical Right Alt also
selects the variant's Western European symbols and dead keys.

`../../../home/caelestia.nix` passes the system's variant/options to Hyprland;
`../../../home/input.nix` does the same for Plasma. The normal locale Compose
table remains available, but the Caps layer does not use it. Menu retains its
normal meaning.

| Hold Caps + | Output |
| --- | --- |
| A / O / U | ä / ö / ü |
| Shift + A / O / U | Ä / Ö / Ü |
| S | ß |
| E | € |
| Minus | – |
| Grave | ^ |

Run `nix build --impure --file modules/input/keyd/tests/symbols.nix --no-link`.
The isolated fixture compiles the pinned keyd parser/event engine, supplies real
Caps/Shift/key press-release events, and passes emitted events through the
configured XKB keyboard state. It checks all ten mappings, both modifier orders
for uppercase, consecutive symbols, balanced releases and ordinary US input.
It opens no keyboard devices and injects no live input. Physical shortcuts and
application handling still need live desktop acceptance after deployment.

# Caps symbol layer

## Intentions

- Hold Caps Lock to type German letters and common symbols on the US desktop
  layout; Caps Lock itself never toggles capitalization.
- Use standard Compose macros consistently so applications can use their built-in
  Compose table rather than depending on keyd's private Cancel encoding.

`../default.nix` imports this module. `../../../home/input.nix` enables the normal
locale Compose table for applications reading `~/.XCompose`. The module maps
the Menu/Compose key to `Multi_key` with `compose:menu`; Hyprland and Plasma
consume that same option. A physical Menu key consequently starts Compose.

| Hold Caps + | Output |
| --- | --- |
| A / O / U | ä / ö / ü |
| Shift + A / O / U | Ä / Ö / Ü |
| S | ß |
| E | € |
| Minus | – |
| Grave | ^ |

Applications must support Compose input. Already-running applications may cache
Compose tables; reopen the application after changing `~/.XCompose` if needed.
The terminal console is not a desktop Compose client.

Run `python3 -B modules/input/keyd/tests/symbols.py LIBXKBCOMMON COMPOSE KEYD XKB_CONFIG_ROOT`
from the repository, supplying the selected packages' `lib/libxkbcommon.so`,
`share/X11/locale/en_US.UTF-8/Compose`, `bin/keyd`, and `share/X11/xkb` paths. The fixture checks
all ten mappings against libxkbcommon and validates the generated keyd config
without injecting input. Physical shortcuts and application handling still need
live desktop acceptance after deployment.

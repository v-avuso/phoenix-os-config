# Contextual radial menus

## Intentions and ownership

Provide contextual menus with reliable holds, isolated launched applications and
managed settings while preserving unrelated application state.

- `default.nix` owns settings/menu baselines, package wrapping, the portal hold patch,
  settings reconciliation and the user service. It composes the concrete desktop adapter.
- `shortcut-hold.patch` feeds portal deactivation into Kando's existing input flow.
- `tests/` owns schemas, selection, package and persistence checks.
- [Hyprland integration](hyprland/README.md) owns compositor commands, bindings,
  window rules, session target, game bypass and their tests.

Import `default.nix` and enable `phoenix.kando.enable`. Current Phoenix wiring uses
Hyprland, native Wayland and the fixed side-button filter in
`modules/input/mouse-side-button-debounce`. The parent is a separation of reusable
Kando responsibilities, not a claim that another desktop is supported.

F23 opens the Global menu; F24 selects an application-specific menu or its fallback.
Hold and move 100 px to execute; release at center cancels. The Global menu contains
Overview, Terminal, Next workspace, Blank screen, Close window, Audio, Previous
workspace and Files. Firefox and ChatGPT menus provide Toggle sidebar
(Ctrl+Shift+S); Kando matches app names/titles rather than browser URLs.

Private JSON baselines reset at service start. Promote GUI experiments before
restarting Kando; caches and unrelated application state are not reconciled.
The service uses `--close-menu` to start in the background with a tray icon;
launching its desktop entry opens the editor. Declarative JSON changes retain their
managed service restart semantics. Blank screen uses Caelestia's idle command.

## Checks and rollback

```sh
nix build --impure --file home/kando/tests/packaging.nix --no-link
```

This checks the exact schemas, context/menu selection, portal hold patch, package
wrapper and Hyprland adapter without launching Electron or a compositor. Static
checks do not prove physical input behavior; runtime validation remains pending.
See the adapter's [practical test and rollback](hyprland/README.md#first-practical-test-and-rollback).
`phoenix.kando.gameButtons = "keys"` restores game F23/F24 passthrough.
`phoenix.kando.gameBypass = false` restores unconditional desktop bindings;
`phoenix.kando.enable = false` disables the whole module on the next authorized apply.
Preparation and tests do not deploy, reload, restart services or interrupt games.

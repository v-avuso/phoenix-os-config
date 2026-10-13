# Contextual radial menus

Import `default.nix` and enable `phoenix.kando.enable`. The host must supply
Hyprland and the side-button filter in `modules/input/mouse-side-button-debounce`.
The private JSON baselines reset at service start. F23 opens the global menu;
F24 selects an application-specific menu or its fallback. Hold and move 100 px
to execute; release at center cancels. A Kando-only focus rule preserves normal
focus-follows-mouse after closure. Native Wayland and the pinned portal hold
patch are required for this integration.

The user service passes upstream's `--close-menu` startup action, keeping Kando
in the background with its tray icon instead of opening the settings editor.
Launching its desktop entry manually still opens the editor. Declarative JSON
changes trigger a managed service restart after settings reconciliation.

The Global menu is: Overview north, Terminal northeast, Next workspace east,
Blank screen southeast, Close window south, Audio southwest, Previous workspace
west, Files northwest. Overview uses the monitor workspace module's HyprExpo;
workspace arrows target the pointer monitor and wrap through its five slots.
Close window uses Hyprland's normal close dispatcher (the Super+Q action).
Blank screen uses Caelestia's idle activation so subsequent input restores it.

Firefox and the ChatGPT desktop menu provide Toggle sidebar northwest
(Ctrl+Shift+S). Kando matches application names/window titles, not browser URLs;
the Firefox entry therefore applies to every tab.

From the repository root, run:

```sh
nix build --impure --file home/kando/tests/packaging.nix --no-link
```

The fixture exercises exact upstream schemas, context selection, hold/release
and menu selection without live input. Physical mouse acceptance remains separate.

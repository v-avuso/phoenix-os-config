# Contextual radial menus

Import `default.nix` and enable `phoenix.kando.enable`. The host must supply
Hyprland and the side-button filter in `modules/input/mouse-side-button-debounce`.
The private JSON baselines reset at service start. F23 opens the global menu;
F24 selects an application-specific menu or its fallback. Hold and move 100 px
to execute; release at center cancels. A Kando-only focus rule preserves normal
focus-follows-mouse after closure. Native Wayland and the pinned portal hold
patch are required for this integration.

From the repository root, run:

```sh
nix build --impure --file home/kando/tests/packaging.nix --no-link
```

The fixture exercises exact upstream schemas, context selection, hold/release
and menu selection without live input. Physical mouse acceptance remains separate.

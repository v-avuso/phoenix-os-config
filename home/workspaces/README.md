# Monitor workspaces and overview

Import `default.nix` with the same `nixpkgs-unstable` input as the running
Hyprland. Set `phoenix.workspaces.monitors.<output>.first` for each output;
`phoenix.workspaces.count` defaults to five. Ranges must not overlap.
Consume `phoenixWorkspacesHyprLua` in the compositor's Lua configuration.

Phoenix uses DP-1 (left) 1–5, HDMI-A-2 (middle) 6–10, and DP-2 (right) 11–15.
Workspaces are persistent and monitor-bound. `phoenix_workspace_step(1)` and
`phoenix_workspace_step(-1)` select the pointer monitor and wrap inside its
range, including empty slots. This is a configured set, not a Hyprland hard
limit: other workspace IDs can still be created through other bindings.

HyprExpo opens with `hyprctl eval 'hl.plugin.hyprexpo.expo("on all")'`. Click a preview
to switch; drag a window preview into another workspace, including on another
monitor; Escape cancels. The package pins upstream source and uses the running
compositor's Nixpkgs plugin builder. Recheck compatibility on compositor updates.
The automatic grid centers partial rows: five workspaces appear as three above
and two below. A one-line upstream patch includes persistent empty workspaces in
that grid. Grid previews move windows between workspaces; dropping within the
same workspace does not rearrange the tiled layout. Use normal Super+drag outside
the overview to rearrange tiled windows.
Caelestia's five-slot unoccupied view follows the active numeric group, so the
bar shows the matching range even for empty workspaces.

Changing ranges does not renumber existing windows/workspaces. Before the first
activation, preserve existing placement by moving windows from old IDs to unused
IDs in their monitor's new range; do not automatically apply this at every login.

```sh
nix shell --inputs-from . nixpkgs#lua --command lua home/workspaces/tests/navigation.lua home/workspaces/navigation.lua
```

This checks navigation without live input. Overview rendering and physical
drag/drop require runtime acceptance.

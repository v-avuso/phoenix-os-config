# Game windows

## Intentions

Prevent incorrect floating, fullscreen overlays and workspace/monitor association
by keeping classified game windows tiled underneath fullscreen. Respect existing
placement without a daemon or plugin. Preserve existing Alt-Tab and monitor selection.
Regular desktop cycling and floating applications must retain their behavior.

`default.nix` supplies Lua to Caelestia after upstream rules and bindings.
`game-windows.lua` owns classification and tiling reconciliation.

## Policy and limits

Classification reuses Caelestia's `game` tag (Steam numeric classes,
`steam_app_default`, Gamescope) and native `content_type = "game"`.
Both static and dynamic (`game*`) tags count. Fullscreen XWayland alone and Wine
`.exe` classes are deliberately insufficient: neither establishes that an app is
a game. The public Lua window API exposes no actual pointer-constraint status.

Unclassified Battle.net/Wine games, including WoW, need a verified exact class:

```nix
# Home Manager configuration; use the actual class reported by hyprctl clients.
phoenix.gameWindows.extraClasses = [ "wow.exe" ];
phoenix.gameWindows.excludedClasses = [ "a-game-dialog-class" ];
```

`wow.exe` is an example, not a verified class for this installation. Exclusions
override extra classes and game tags. Disable the whole policy with
`phoenix.gameWindows.enable = false`. Same-class game dialogs cannot be separated
by this simple class exception mechanism; runtime validation remains pending.

Static `tile` rules avoid fullscreen-at-creation dependence. Event callbacks cover
late classification and subsequent fullscreen/rule updates, unsetting floating
only for the event's mapped game window. They do not move workspaces or explicitly
toggle fullscreen. An already inconsistent live window is not repaired on config
load. No restart of a running game is required for preparation or commit. Manual floating of classified games can be
reversed by subsequent rule updates; exempt the class if floating is intentional.

Game rules disable hover focus, focus requests and forced pointer confinement.
Alt-Tab, Shift-Alt-Tab, group cycling and workspace shortcuts are unchanged.
There is no automatic cursor movement or monitor-focus selection in this component.
`no_follow_mouse` helps avoid hover focus after a normal focus change, but does
not directly release an active constraint or prevent all reactivation paths.
VM-style release at the current position until click is **not implemented**.

Kando is **unchanged**. The existing hardware filter replaces BTN_SIDE (275) and
BTN_EXTRA (276) with F24/F23 before Hyprland. Declining an `auto_consuming` binding
would forward keyboard keys, not mouse buttons. Moving interception back to mouse
bindings also loses the existing tested portal hold/release path. Correct forwarding
needs a separate bounded input-path trial; no speculative remapping is added here.
Buttons therefore still do not reach games as original mouse events.

## Evidence and reuse decision

Inspected the locked Hyprland 0.56.2 source, rather than relying solely on current
wiki syntax: `LuaWindow.cpp` exposes `tags`, `content_type`, visibility and focus
history; `TagKeeper.cpp` appends `*` to dynamic tags; `LuaWorkspace.cpp` exposes
`special` and `active`; `FocusState.cpp` deactivates the old surface constraint on
keyboard focus change. Native rules/queries/dispatchers are sufficient for this
bounded approximation. No compositor compilation or polling is needed.

- [Window rules](https://wiki.hypr.land/Configuring/Basics/Window-Rules/) distinguish static tile from dynamic focus effects.
- [Bindings](https://wiki.hypr.land/Configuring/Basics/Binds/) document conditional consumption and inhibition flags.
- [Dispatchers](https://wiki.hypr.land/Configuring/Basics/Dispatchers/) supply existing focus and cycling behavior.
- [Pinned implementation](https://github.com/hyprwm/Hyprland/tree/v0.56.2/src) is the compatibility reference.
- [Pointer ungrab request](https://github.com/hyprwm/Hyprland/issues/3207) describes the remaining direct-ungrab use case.
- [Kando triggers](https://kando.menu/opening-menus/) and [menu conditions](https://kando.menu/config-files/) do not restore mouse events already replaced upstream.

## Proposed direct-release alternative (not implemented)

In the locked source, `Actions::releaseInputCapture()` only calls
`PROTO::inputCapture->forceRelease()`. `CInputManager::unconstrainMouse()`
deactivates ordinary constraints internally, but is not exposed through Lua.
`CPointerConstraint::activate()` can reactivate through focus changes and new
constraint requests. `no_follow_mouse` and `confine_pointer = false` do not guard
those paths. No matching maintained plugin was identified in a bounded search;
this is not proof that none exists.

The smallest credible alternative is a narrowly scoped compositor patch:

- Add a Lua dispatcher for release-until-click; retain a weak reference to the
  released window/surface, without selecting any window/monitor or moving the cursor.
- Deactivate existing ordinary constraints and guard activation of persistent and
  newly created constraints for that window until an actual click on it.
- Restore capture on that click, with lifecycle cleanup for destruction, logout
  and lock transitions. Reject hover/activation-request recapture.
- Verify relative-motion delivery, client cursor hiding and client-requested warps
  while released: deactivation alone may leave a game receiving camera movement or
  hiding/moving the cursor. Cover XWayland and native clients.
- Compose release with the existing Alt-Tab cycle only after checking ordering:
  ordinary applications must retain existing behavior. Whether game Alt-Tab also
  cycles windows or serves only as release needs an explicit operator choice.

This is a source-based design proposal, not a proven lightweight implementation.
A plugin could register a dispatcher and mouse-click listener, but guarding
`CPointerConstraint::activate()` requires internal function hooks in this version.
That adds exact-version/header ABI and hook-failure risks. A small source patch
has clearer lifecycle ownership but rebuilds Hyprland and needs upgrade rebasing;
changing its package also requires checking the existing HyprExpo compatibility.
Recommend a bounded disposable-compositor proof before production integration:
locked/confined, persistent/oneshot/recreated constraints, cursor position unchanged,
hover across the game, click restore, one/three monitors, normal cycling, lock/exit,
and Steam/Wine/native clients. No patch/plugin is added without agreement on this
alternative. No running compositor is launched by this task.

Source references:
[portal release](https://github.com/hyprwm/Hyprland/blob/v0.56.2/src/config/shared/actions/ConfigActions.cpp),
[ordinary constraint lifecycle](https://github.com/hyprwm/Hyprland/blob/v0.56.2/src/protocols/PointerConstraints.cpp),
[input handling](https://github.com/hyprwm/Hyprland/blob/v0.56.2/src/managers/input/InputManager.cpp),
[plugin API](https://github.com/hyprwm/Hyprland/blob/v0.56.2/src/plugins/PluginAPI.hpp).

## Safe checks and pending runtime validation

```sh
nix shell --inputs-from . nixpkgs#lua --command lua home/game-windows/tests/game-windows.lua home/game-windows/game-windows.lua
nix eval --no-write-lock-file .#nixosConfigurations.metal-4tb.config.system.build.toplevel.drvPath
nix flake check --no-build --no-write-lock-file .
```

Git flakes exclude untracked files. Before evaluating, stage only these intended
new files, or validate a disposable Git copy containing the intended patch. Staging
does not require committing. Automated tests model policy, not compositor/input IO.

When ready, the **operator**, from this checkout, runs:

```sh
PHOENIX_TARGET=metal-4tb phoenix-test --worktree /home/v/repos/code/phoenix-os-config
```

The installed command is `phoenix-test`, not `phoenix test`. This task does not run it.

Runtime validation is pending and is not a prerequisite for this source-only commit.
When games are next used naturally after an operator-authorized deployment:

1. Check tiled/fullscreen state and registered/rendered monitor; no forced restart
   or interruption of No Man's Sky is required by this workstream.
2. Switch workspaces on all screens; check for overlays/stale game surfaces.
3. Verify existing Alt-Tab/Shift-Alt-Tab behavior; no automatic monitor selection
   was added. Record capture behavior separately; direct release remains unimplemented.
4. Check existing Kando hold/move/release behavior immediately after Alt-Tab and on
   desktop. Mouse-button passthrough in games remains unsupported by this patch.
5. Verify Firefox/desktop cycling, group cycling, workspace keys and floating dialogs.
6. Verify WoW's class, opt it in if necessary, then repeat window/capture/dialog checks.
7. Repeat with disconnected monitors and one monitor; check window placement.
8. Test a native game content hint and an unclassified fullscreen XWayland app;
   the latter must retain normal behavior.

Before deployment, rollback is simply removal of the added Caelestia import/Lua
insertion and this directory. After a manual `phoenix-test`, reboot restores the
unchanged boot profile, or disable the policy and manually test the corrected source.
Do not discard unrelated work when reverting these files.

# Hyprland game windows

## Intentions and ownership

Prevent incorrect floating, fullscreen overlays and workspace/monitor association
by keeping classified game windows tiled underneath fullscreen. Preserve placement,
ordinary floating applications and existing Alt-Tab behavior without a daemon/plugin.

This directory owns Hyprland gaming window behavior. Caelestia imports `default.nix`
directly; no extra hierarchy modules are needed just to group files.

- `classification.lua` is a pure predicate over Hyprland window metadata and exact
  class overrides. It makes no compositor calls.
- `game-windows.lua` owns initial rules and bounded event reconciliation.
- `game-overrides.lua` owns narrowly matched, game-specific startup workarounds.
- `default.nix` preserves `phoenix.gameWindows.*` and initializes the shared predicate
  before [Kando's Hyprland adapter](../../../kando/hyprland/README.md).
- `tests/` exercises classification, rules, late changes and exclusions.

## Classification and controls

Reuse Caelestia's `game` tag (numeric Steam classes, `steam_app_default`, Gamescope)
and native `content_type = "game"`. Both `game` and dynamic `game*` tags count.
Fullscreen and XWayland alone do not establish that a window is a game. Wine `.exe`
names likewise do not identify games, and executable names need not equal window
classes. Unclassified games need an observed exact class opt-in. No individual game
class is configured by default; opt-in and exclusion lists are empty.

```nix
# Home Manager configuration; replace with actual Hyprland window classes.
phoenix.gameWindows.extraClasses = [ "observed-game-class" ];
phoenix.gameWindows.excludedClasses = [ "observed-dialog-class" ];
```

Exclusions override tags, content hints and opt-ins. Same-class dialogs cannot be
separated by this simple class mechanism. Disable automatic rules with
`phoenix.gameWindows.enable = false`; classification remains available for Kando.
Disable only Kando interception bypass with `phoenix.kando.gameBypass = false`.
Public option names and defaults are unchanged by the directory refactor.

Static `tile` handles games recognized at creation. `window.open`,
`window.fullscreen` and `window.update_rules` callbacks handle late classification
or subsequent changes, unsetting floating only for that mapped game window.
Callbacks do not move workspaces, explicitly toggle fullscreen, run subprocesses or
steal focus. Manual floating can be reversed on later rule updates; exempt its class
if intentional. The policy does not repair an already inconsistent window at load.
Game rules also retain `no_follow_mouse`, disabled focus requests and disabled forced
pointer confinement. These do not implement VM-style pointer release.

## Evidence and deferred pointer release

The prior implementation was checked against the
[official rules documentation](https://wiki.hypr.land/Configuring/Basics/Window-Rules/)
and exact [Hyprland 0.56.2 source](https://github.com/hyprwm/Hyprland/tree/v0.56.2/src).
Static tile requires event reconciliation for late metadata changes; dynamic tags
have a `*` suffix. This structural refactor retains those decisions and actions.

Direct release-until-click remains a separate unimplemented feature. In 0.56.2,
`release_input_capture()` releases portal capture, not ordinary game constraints.
Lua exposes neither direct ordinary-constraint release nor suppression until click.
Research a lightweight maintained plugin first; a plugin may need version-sensitive
internal hooks, and a narrowly scoped patch is the remaining alternative. Any future
implementation must be optional and disabled by default, with no change to the
Hyprland package derivation unless explicitly enabled. Release must leave the
cursor/monitor unchanged and allow movement until a game click restores capture. Relative motion, cursor hiding/warps, persistent
and recreated constraints require a bounded proof before either alternative.
See [constraint lifecycle](https://github.com/hyprwm/Hyprland/blob/v0.56.2/src/protocols/PointerConstraints.cpp)
and [portal release](https://github.com/hyprwm/Hyprland/blob/v0.56.2/src/config/shared/actions/ConfigActions.cpp).
Alt-Tab remains unchanged; there is no automatic monitor selection.

## Checks, pending runtime validation and rollback

```sh
nix shell --inputs-from . nixpkgs#lua --command lua home/hyprland/gaming/windows/tests/game-windows.lua home/hyprland/gaming/windows/game-windows.lua home/hyprland/gaming/windows/classification.lua
nix shell --inputs-from . nixpkgs#lua --command lua home/hyprland/gaming/windows/tests/game-overrides.lua home/hyprland/gaming/windows/game-overrides.lua
nix eval --no-write-lock-file .#nixosConfigurations.metal-4tb.config.system.build.toplevel.drvPath
nix flake check --no-build --no-write-lock-file .
```

Moved/new files must be Git-visible for flake checks. Stage only intended files or
use a vetted disposable Git copy. Static tests do not prove runtime behavior.
Runtime validation remains pending and requires no game reopening for this refactor.
On later natural use, check fullscreen/tiling, workspace overlays, monitor assignment,
ordinary dialogs and the adapter's side-button hold/focus tests, including one monitor.

Rollback controls are `phoenix.gameWindows.enable = false` and
`phoenix.kando.gameBypass = false`. Retain classification while Kando consumes it;
remove that dependency before removing the entire module. The operator may apply
corrected source when ready. To undo only this refactor, reverse its moves/wiring
while retaining the previously prepared Kando work; do not reset the whole worktree.
Only source preparation, non-deploying checks and an authorized local commit are
performed; no activation, reload, restart or game interruption is used for validation.

## World of Warcraft startup fullscreen workaround

WoW's Fullscreen (Windowed) mode can initially leave Caelestia visible until
`Super + F` enables compositor fullscreen. A read-only sample on 2026-10-25 confirmed
both `initialTitle = "World of Warcraft"` and `initialClass = "steam_app_default"`,
alongside `xwayland = true` and the existing `game*` tag. Thus the identifying title
is already available for a static rule; no title-change listener is needed.

The override requires that exact title, exact class and XWayland together, and sets
only native `fullscreen = true`. It does not match differently titled Battle.net,
Wine dialogs or other applications sharing that class. Existing game tiling remains
responsible for `floating = false`. Hyprland 0.56.2 applies static fullscreen once
at mapping, so manual fullscreen exits remain possible; there is no recurring
enforcement, input change or workspace/monitor assignment. Different/localized
initial titles will retain manual `Super + F` behavior.

Runtime validation is pending. After an authorized deployment, check the next
natural WoW launch with `hyprctl -j activewindow`: expect `fullscreen: 2` and
`floating: false`, the intended monitor, no visible panel and unaffected dialogs.
Toggle `Super + F` off/on and confirm normal Kando/side-button behavior after
Alt-Tab and clicking back. This static rule does not change an already open window;
no WoW restart is required now, but verification needs a subsequent launch.
To roll back only this workaround, revert its commit (preserving other work).

## Persistent grabbing cursor: diagnosis pending

The operator observed a closed hand across desktop/game surfaces and, separately,
a system cursor inside the game. Neither trigger nor current cursor ownership is
established. Read-only diagnostics confirmed the compositor version and relevant
input bindings, but its bounded log buffer contained no matching cursor/drag events.
The public Lua/IPC queries inspected do not expose the active cursor override owner.

In pinned 0.56.2, `layout/supplementary/DragController.cpp` installs a `grabbing`
override for window moves and normally clears it on drag end. Clients can also
request cursor images. Thus a stale compositor drag/override and a Wine/client
cursor are candidates; the shape alone proves neither. The existing Sweet-cursors
theme spelling is correct; no theme reset, driver change, process restart or global
cursor override is justified by this evidence. Upstream stale-cursor fixes already
listed in 0.56.1 do not establish a remedy for this unknown trigger.

Smallest later reproduction: note the last action (game camera drag, Super+window
move, Kando hold or Alt-Tab), release all mouse buttons/modifiers, then observe
whether the hand persists over a native desktop app and after a normal window
move ends. Capture `hyprctl -j activewindow`, `hyprctl -j binds` and the bounded
`hyprctl rollinglog` around the event. Do not reopen the game solely for this task.
If it is clearly an unfinished window move, releasing its initiating button and
modifier is the normal recovery path; no unverified reset command is installed.
See the pinned [drag controller](https://github.com/hyprwm/Hyprland/blob/v0.56.2/src/layout/supplementary/DragController.cpp)
and [cursor overrides](https://github.com/hyprwm/Hyprland/blob/v0.56.2/src/pointer/cursor/CursorShapeOverrideController.cpp).

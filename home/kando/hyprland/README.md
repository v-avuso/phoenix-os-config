# Kando on Hyprland

## Intentions and ownership

Preserve desktop menu holds while allowing classified games to receive native side buttons.
Keep compositor commands and input routing separate from Kando settings/persistence.

- `default.nix` supplies desktop commands, the session target, window rules and Lua
  wiring to the parent module; it preserves the existing public options.
- `shortcuts.lua` owns conditional bindings; `tests/` owns routing and rollback checks.
- Caelestia initializes the shared game predicate before this adapter. No other
  compositor is supported or implied by this separation.

`shortcuts.lua` owns the only F23/F24 bindings. Caelestia passes it the predicate
from [game windows](../../hyprland/gaming/windows/README.md); disabling automatic tiling does not
disable classification. Desktop presses retain their existing portal menu actions.
For classified games, the default `phoenix.kando.gameButtons = "mouse"` translates
F23 back to BTN_EXTRA (276) and F24 back to BTN_SIDE (275), consuming the transport
F-keys. Wine's X11 mouse driver maps the resulting X buttons to XBUTTON2/XBUTTON1.
The fixed-device filter and its 180 ms stable-release delay remain unchanged.

`phoenix.kando.gameButtons = "keys"` restores the prior `{ ok = false }` plus
`auto_consuming` key passthrough. This preserves existing F23/F24 game bindings if
needed. `phoenix.kando.gameBypass = false` restores unconditional desktop menus.

Routing is fixed for each physical hold. A desktop press keeps its Kando portal
release even if focus changes to a game; a game press cannot open Kando on release
after Alt-Tab. The next press uses current focus immediately. Both keys have
independent state. Desktop shortcuts also work with modifiers held and bypass
application shortcut inhibition so those changes cannot strand portal releases.
Session-lock restrictions are unchanged. Config reload/service shutdown during a
hold is outside this adapter's guarantee; release the buttons before manual changes.

The existing fixed-device filter remains unchanged: BTN_EXTRA (276) emits evdev
F23 (193), BTN_SIDE (275) emits F24 (194), and stable release is delayed by 180 ms.
Each binding latches an action for the full hold. Both `global()` and
`send_shortcut()` request a release callback; native handling clears the request
before invoking it. Game-origin holds cannot activate a desktop menu on release,
and desktop-origin holds always finish their portal release. In keys mode a
declined press requests no callback, and native handling forwards the paired release.

Native translation uses `send_shortcut({ mods, key = "mouse:275" })` (276 for F23)
without a window selector, so it does not warp the cursor or change pointer focus.
It follows ordinary pointer focus; the seat releases held buttons on surface leave.
It does not target a background game after moving the pointer elsewhere. Held
modifier keys are sampled on both edges. The pinned dispatcher sends a temporary
modifier mask and clears it afterwards; physical Ctrl/Shift combinations and lock
state behavior still need practical validation. No modifier-key synthesis is added.

The implementation relies on inspected Hyprland 0.56.2 behavior:
[press/release forwarding](https://github.com/hyprwm/Hyprland/blob/v0.56.2/src/managers/KeybindManager.cpp),
and [global/native shortcut release callbacks](https://github.com/hyprwm/Hyprland/blob/v0.56.2/src/config/lua/bindings/LuaBindingsDispatchers.cpp).
Native shortcuts, the existing remapping and Kando hold patch supply the workflow;
only focus-based routing and per-hold state are added. Recheck these contracts on
compositor upgrades.


The adapter's Overview command uses HyprExpo; workspace commands target the pointer
monitor's five-slot range. Close window uses the normal Hyprland close dispatcher.
The Kando-only focus/window rule and `hyprland-session.target` remain unchanged.

## Static checks

```sh
nix shell --inputs-from . nixpkgs#lua --command lua home/kando/hyprland/tests/shortcuts.lua home/kando/hyprland/shortcuts.lua home/hyprland/gaming/windows/classification.lua
nix build --impure --file home/kando/hyprland/tests/packaging.nix --no-link
```

The [parent packaging fixture](../tests/packaging.nix) also runs these checks.
Tests model the pinned native press/release boundary and verify the existing device
mapping, integration and rollback settings. Runtime input validation remains pending.

## First practical test and rollback

After operator-authorized deployment (not performed during preparation):

1. Verify the game's exact class is classified by a game tag/content hint or configure
   `phoenix.gameWindows.extraClasses` with its actual class. Do not infer that every
   Wine window is a game. Use observed window metadata, not an executable filename.
2. Focus the game with the pointer over it, bind Mouse4/Mouse5, and press/hold/release
   each side button (F23/F24 in keys mode).
   Check that both edges arrive and Kando stays closed. Repeat holding both buttons,
   Ctrl/Shift combinations, and moving across windows/monitors during a hold.
3. Alt-Tab normally to a desktop app; each side button must immediately open its
   existing Kando menu. Check hold/move selection and center-release cancellation.
4. Click back into the game and repeat step 2. Test a desktop-origin hold released after
   focus changes, a game-origin hold released after Alt-Tab, and modifier changes
   during a desktop hold; check for stuck actions or menus.
5. Check Firefox/desktop shortcuts, floating dialogs and existing Alt-Tab behavior.
   Pointer-constraint release itself remains a separate, unimplemented feature.

To disable bypass, set `phoenix.kando.gameBypass = false` and let the operator apply
the corrected source when ready; this restores the original two unconditional
bindings and retains game tiling. It does not require an input-service restart.
No rollback command is run automatically. To roll back only native translation, use `phoenix.kando.gameButtons = "keys"`.
Source changes can be reversed selectively; do not discard unrelated edits or the
prior tiling commit.

## Button delivery evidence and remaining uncertainty

Read-only inspection on 2026-10-25 confirmed the installed 0.56.2 compositor,
`steam_app_default` with `game*`, fullscreen 2 and non-floating state, one binding
per transport key, and the named virtual keyboard from the fixed-device filter.
The source filter replaces side buttons with held F23/F24; keyd has no explicit
F23/F24 remapping. The observed correct Kando bypass establishes classification,
but not delivery into the game UI. No physical events were injected or captured.

The previous route delivered keyboard events, not Windows mouse side buttons.
Upstream Wine's [keyboard implementation](https://github.com/wine-mirror/wine/blob/master/dlls/winex11.drv/keyboard.c)
includes F1–F24 virtual-key handling; [DirectInput definitions](https://github.com/wine-mirror/wine/blob/master/include/dinput.h)
provide conventional function-key scan codes only through F15. This supports a
key-recognition mismatch as a hypothesis, not proof about the running game's
input API or exact Wine runner. The loss boundary remains untraced without an
interactive input trial. Native translation avoids dependence on F23/F24 recognition;
[Wine's mouse implementation](https://github.com/wine-mirror/wine/blob/master/dlls/winex11.drv/mouse.c)
provides paired XBUTTON down/up mappings. These Wine sources are upstream evidence,
not verification of the installed runner or WoW's UI. The Hyprland dispatcher and
seat lifecycle were inspected against exact locked 0.56.2 sources. A passing Lua
model does not prove game-side acceptance or pointer-frame timing for native clients.

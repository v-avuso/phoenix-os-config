# OPie Visual Delay

## Intentions and status

Delay only OPie's visuals, leaving bindings, cursor selection, quick actions and
secure execution with OPie. This version uses narrowly scoped internal post-hooks
explicitly authorized by the operator. It needs no wrapper or OPie source patch.

**Experimental implementation; client acceptance remains required.** The local proof runs OPie's real
renderer and notification Lua with simulated WoW APIs. Actual displayed frames,
protected actions and combat taint remain in-game acceptance; do not call them proven.

The Settings section contains only controls. `enabled`, integer `delayMs` and integer `fadeMs` live
under `PhoenixWoWToolkitDB.features.opieVisualDelay`. Fresh defaults are on / 50 ms delay / 100 ms fade-in;
a previously saved disabled preference from the old placeholder remains disabled.
The slider and numeric field accept 0–1000 ms in 1 ms increments. Enter/focus loss
commits numeric input; Escape restores the saved value. Zero delay means immediate display, including bypassing the fade. Zero fade duration
disables fading. Fade duration has its own slider and exact numeric field.
Changing the delay while waiting uses the original opening time. Enabling while a
ring is already visible takes effect on its next opening, without hiding it mid-use.

## Exact source boundary

Inspected installed **OPie 8.10.2** on Retail and Forever; interfaces **120105** and
**16001** are runtime compatibility gates. The Forever option defaults off until a
live trial establishes rendering, protected actions and combat behavior. Source paths
below are relative to installed `AddOns/OPie`:

| Location | Evidence and integration |
|---|---|
| `OPieCore.lua:127` | The protected input/action button has generated name `OPieRT-<8 hex>-<4 hex>`. It stays under OPie's control. Discover it with `EnumerateFrames`, independently of parenting; require exactly one protected Button with this identity and `NotifyState`. |
| `OPieCore.lua:1215–1265` | `NotifyState` is ordinary Lua, called by secure snippets via `CallMethod`. It dispatches `securecall(ORI.Show/Hide, ...)`. A `hooksecurefunc` observer runs **after** the complete original callback; no click, binding, secure snippet or protected attribute is replaced. |
| `UI/RingView.lua:97–154` | Separate main and `OPieVisualElementsProxy` roots contain the central ring, slices and ghost groups. The unnamed main root is FULLSCREEN, level 100, 150×150 (allowing less than 0.05 units of client rounding per dimension), with the OPie pointer texture. Discovery requires exactly one matching main frame and notification frame. Pointer matching accepts local texture paths or file IDs and skips secret values. |
| `UI/RingView.lua:781–812` | Native animation repeatedly writes alpha. Post-hooks record the intended alpha and immediately reassert zero while gated. All original OnUpdate, position, scale, cooldown and selection updates keep running. |
| `UI/RingView.lua:822–880` | `Show` completes before the notification observer; Lua execution does not yield in this path. `Hide` starts a closing animation, so OnHide is too late to identify a cancelled pending reveal. Observe logical `close` instead. |
| `UI/RingView.lua:489–529`, `Libs/NotGameTooltip.lua` | The separate tooltip is read through `OPie.HUM.NotGameTooltip`. Only while it belongs to the visual proxy is its alpha gated. Show, alpha and owner changes are observed; changing owner releases suppression. |

Source SHA-256 used by the local proof:

```text
OPieCore.lua     1a15a57015984a206732c6c17426fcf92d23145d0aa26aa4669e550ef17947ba
UI/RingView.lua  c9fa518e33f6480fea27fb218f98c640cced5f90389213a984bc9c38fa974b91
```

`Renderer.lua` owns discovery, alpha gating and timer cancellation; `Feature.lua` owns feature registration and settings. No OPie source is
copied or redistributed. Its all-rights-reserved license remains intact.
[Author release notes](https://www.townlong-yak.com/addons/opie/release/8.10)
identify this version and appearance compatibility changes.

## Lifecycle and limits

An `open` notification starts a visual gate after original rendering setup finishes
and before the Lua event returns. `C_Timer.After` starts the reveal. An owned frame runs `OnUpdate` only during the
fade, multiplying the latest native alpha by a linear 0–1 factor. OPie's own
animation remains active. Closing stops the fade and freezes that factor through
the native close animation; it cannot complete an abandoned reveal.
Each opening/settings transition changes a serial, invalidating old callbacks.
A `close` cancels reveal and keeps a still-hidden ring suppressed throughout native
fade-out. Nested `switch` notifications preserve the first deadline or already-visible
state. Disable restores recorded native alpha and cancels pending callbacks and fades.
Changing settings during a fade completes that fade immediately; changing the
delay while waiting still uses the original opening time.

Only alpha on verified ordinary visual frames is changed. No Hide, SetParent,
SetScript on OPie frames, WrapScript, secure-action override, input timer or error-catching fallback
is used by the adapter. `hooksecurefunc` retains the original callback; its observer
is not a new source of protected execution authority. Unknown versions/interfaces,
missing notification methods, ambiguous discovery or protected visuals leave the
feature unavailable, with no compatibility essay in the UI. Unexpected client errors
are allowed to surface rather than being swallowed.

There is still runtime risk in an internal integration. Version/shape checks are
not a cryptographic runtime hash of OPie or proof of compatibility with another
add-on wrapping those methods. The default Mirage skin is the inspected case;
custom skins rendering outside these roots or ignoring parent alpha are unverified.
First-frame suppression depends on normal WoW frame presentation after synchronous
Lua execution. Timers and screen presentation are frame-rate limited: 1 ms settings
precision does not promise 1 ms display accuracy. An added observer takes execution
time, but introduces no intentional wait in OPie's action path.

On upgrades, leave the gate closed to unverified versions. Inspect exact source,
notification ordering, frame identities, skin/tooltip parenting and protection;
update version/interface checks only with a repeated proof and client acceptance.
Prefer an upstream visual-only setting if one becomes available. Do not broaden
matches or intercept secure input to make a failed structural check pass.

## Local proof and in-game acceptance

Run with a separately installed OPie tree; its original code is read, not modified:

```sh
lua features/opie-visual-delay/tests/test.lua . \
  '/path/to/_retail_/Interface/AddOns/OPie'
```

Adding `baseline` as the third argument deliberately fails `ring leaked`, showing
that native OPie immediately makes its visual alpha nonzero. With hooks, the proof
passes taps, cursor/modifier changes during hidden updates, holds, repeated/reopened
menus, nested switches, animation-on/off, tooltip ownership, cancellation, restoration,
zero/max delay, partial/completed/cancelled fades, controls, numeric validation, unknown versions/interfaces and changed
frame/method structure. Regressions cover the observed 149.994461 client dimensions,
notification discovery outside direct UIParent children, materially different sizes
and duplicate notification frames. The frame scan skips non-string `GetName()`
results: Blizzard damage-meter entries override that method to return a FontString. It executes unmodified `RingView.lua` and extracts the exact
`NotifyState` callback into an isolated local environment. Frame APIs, protected
snippets and actual casting are not executed in a WoW client.

After separately approved deployment, use a harmless test ring and compare with
**Enable visual delay** off, then on at 50 ms:

1. Tap below 50 ms; compare the normal quick action and verify no opening or closing
   flash. Hold beyond 50 ms, then release with a selected slice.
2. Flick in several directions before reveal; verify the same action as baseline.
   Repeat rapid taps, cancel with Escape/right-click and reopen during fade-out.
3. Use different rings, modifier bindings and nested/embedded/jump rings, including
   transitions while hidden and after reveal. Check ghosts, tooltips and native
   animations on/off, as well as low frame rates.
4. Repeat inside combat with combat-usable actions. Inspect BugSack and protected
   action/taint reporting. Stop on any missed/delayed action, forbidden call or flash;
   the local proof cannot pass this acceptance item.
5. Disable during a pending reveal and after reveal. Check native visuals and ordinary
   tooltips return. Test 0, 1, 50, 250 and 1000 ms, numeric entry/Escape, `/reload` and restart
   persistence. Test fade durations 0, 100 and 1000 ms; close during the fade,
   reopen rapidly and disable mid-fade. Confirm Objective Tracker preferences still work independently.

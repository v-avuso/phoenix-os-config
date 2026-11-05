# Reusing the actual Dialogue UI tooltip

## Outcome and intentions

The real renderer is reusable without recreating its art, fonts, layout, 3D widget or
comparison UI. A source-backed Lua proof passes against installed Dialogue UI **1.0.7**.
This is a research prototype, not a deployed global replacement or a WoW-client visual
proof. The probe is deliberately absent from the add-on TOC. Existing runtime behavior
is unchanged; the reported footer-removal failure remains unresolved.

The next milestone is one real bag-item hover with the actual renderer, stable refresh,
restoration on leave and no interference with quest rewards. Do not build more styling
or broaden source-window coverage before that client trial succeeds.

## Actual extension boundary

- `Tooltip_Base.lua` creates the frame, theme-owned background, DUIFont objects and
  layout. `Tooltip_Private.lua` augments **one shared instance** with model preview,
  source-camera selection, replacement deltas, hotkey hint and data-update handling.
- `DialogueUIAPI.AddItemTooltipProcessorExternal(callback)` is public and passes this
  actual instance to item-annotation callbacks. It is an extension seam for future
  owned additions, but not a factory or an immediate getter. Acquisition through it
  alone would require the first Dialogue UI item tooltip to have appeared already.
- `TooltipSetHyperLink` looks like another public bridge, but its registration API is
  commented out in `CallbackRegistry.lua`. Its object getter creates only a base
  tooltip, not the private preview/comparison renderer. It is not the missing global
  enable switch.
- There is no global export of the add-on namespace or renderer in the inspected files.
  A single read-only `EnumerateFrames` scan can identify the ordinary shared frame by
  its combined method signature, even before its first use. Gate this internal lookup
  to 1.0.7 and reject missing, ambiguous, forbidden or protected candidates. This is an
  unsupported internal adapter, not an upstream-stable public contract. The public
  item callback can subsequently corroborate the discovered instance.

## Important behaviors demonstrated by the proof

**Item dispatch:** `SetHyperlink` derives `isItem` from whether the getter's name contains
`Item`. `GetHyperlink` does not, so this path renders text/model but does not invoke
item comparisons or item processors. The probe calls the original `ProcessInfo` with:

```lua
{ getterName = "GetHyperlink", getterArgs = { fullItemLink }, isItem = true }
```

`SetItemByGUID` is another item-aware route when a GUID is available. Keep full links
or GUIDs; do not reduce candidates to an item ID and lose item-specific data.

**Ownership:** the renderer is shared with quest rewards, widgets, books and other
Dialogue UI integrations. A bounded lease can use it while idle and must yield when
Dialogue UI takes ownership. An old hover's cleanup must never hide a newer quest
reward. The proof exercises a quest takeover and rejects stale release. Do not clone
methods onto another frame: Shift handling and some refresh callbacks close over the
original singleton, so a superficially independent clone is not independent.

**Rendering:** the proof executes the original theme/font selection and model code.
The original model has positive Y offset (`0.33 * modelHeight`), producing the reference's
overhang. Its own source camera is applied on model load. Do not add a separate panel,
reserve an unrelated full-height column, or style native tooltips to imitate this.

**Refresh:** repeat native tooltip postcalls can carry newly allocated data tables for
one unchanged hover. Do not hide/reload the shared model on each callback. The proof
coalesces the same owner/full-link pair; Dialogue UI's existing `TOOLTIP_DATA_UPDATE`
handler owns its data refresh. Dialogue UI can also configure a 250 ms tooltip fade
in its main-frame initialization; repeatedly restarting that fade would be a new bug.
Live timing and item-context changes need client tests, not assumptions from table identity.

**Shift and preferences:** its real Shift toggle and hint work in the proof. They own
`DialogueUI_DB.TooltipShowItemComparison`. A thin adapter should initially honor that
preference, not silently override it or install another comparison controller. Future
Phoenix-specific changes should be scoped to an active owned lease through the public
annotation callback where possible. That callback is queued: verify both current owner
and event item-link identity before applying an extension to a reused tooltip.
Do not replace `ProcessItemExternal`, which Pawn's
integration already uses.

## Selected path and alternatives

| Approach | Fit and cost |
| --- | --- |
| Public item callback alone | Useful for annotations; cannot provide immediate startup acquisition. |
| Version-gated one-time lookup + shared-instance lease | Smallest locally viable probe; no source patch, function replacement, asset copying or polling. Requires lifecycle/fallback validation. |
| Upstream supported getter/render entry point | Best long-term boundary; could replace discovery while retaining the same lease. No upstream message/issue has been sent. |
| Independent renderer factory | Useful for simultaneous sticky item links and bag hovers, but upstream must untangle singleton callbacks. Not a trivial clone. |
| Fork or new imitation | Unnecessary for the first workflow; introduces code/assets permission and maintenance burdens. Not selected. |

The production adapter should remain inside this feature behind the existing dropdown,
with optional DialogueUI dependency detection and ordinary native fallback. First support
GameTooltip-driven equipment hovers, not every simultaneous tooltip. Keep the current-UI
choice intact. A future independent renderer is justified only by demonstrated concurrent
window requirements or additional behavior that cannot be added through the owned lease.

## Remaining risks and client proof

The probe only shows the upstream renderer from an owner/link. It **does not** yet hide
or substitute the native tooltip, wire the feature dropdown, or manage a live hover.
These are required before calling this globally enabled:

1. Observe the native item-processing layer; obtain public full link/GUID and source
   owner. Skip secret/inaccessible data, forbidden/protected/secret-anchored frames,
   unavailable sources and changed Dialogue UI structures. Never catch protected-action
   failures and continue as though rendering succeeded.
2. Render successfully before suppressing the original presentation. Retain its
   lifecycle/input processing; restore only owned visual state on leave, disable,
   unavailable data or quest takeover. No native CVar changes or secure action hooks.
3. Repeated same-item refresh, rapid item switching, Shift, tooltip data updates,
   missing cached data and native comparison anchoring must remain stable. Inspect
   `showDelay`, model reloading and event ownership explicitly when diagnosing flicker.
4. Native TooltipDataProcessor annotations are not automatically transferred: Dialogue
   UI obtains fresh C_TooltipInfo data and runs its own processors. Its integrations
   (such as Pawn/translation) continue, but arbitrary native annotations need an explicit
   preservation strategy or an acknowledged native fallback. Do not silently discard them.
5. Upstream comparison code needs cases for ring/trinket alternatives and combined/paired
   weapons: it calls the delta API per equipped item without the paired arguments used
   by Blizzard's combined comparison path. Do not claim those semantics proven by a
   single-slot bag-item test. Override-item-level contexts also need separate checks.
6. The preview resolves transmog information from item ID internally; bonus/appearance
   variants need a real-item check before adding a scoped full-link appearance adapter.
7. Test ElvUI/ToxiUI, combat and noncombat, quests while bags remain open, and persistent
   ItemRef tooltips. One singleton cannot represent two independently visible candidate
   tooltips. Additional contexts must retain native fallback until proven.

The equipped-item footer is a **separate** feature and remains a failed player acceptance
case. Exact renderer reuse neither diagnoses nor fixes its current native hook/row-match
failure. Capture the live feature availability, ProcessInfo snapshot, expected/actual
footer rows and final font visibility; make the next regression reproduce that evidence
instead of adding another speculative static fix. Do not truncate arbitrary item rows.

## Reproduce the source proof

From the toolkit root:

```sh
python3 tests/run.py --lua /path/to/lua --dialogue-ui /path/to/AddOns/DialogueUI
```

This loads the unmodified installed `CallbackRegistry.lua`, `Tooltip_Base.lua`,
`Tooltip_Private.lua` and `Tooltip_Public.lua` into a simulated frame environment.
The tests assert the real singleton identity, pre-first-hover discovery, public callback,
upstream theme/fonts, overhang/camera, item comparisons, Shift preference, repeat-hover
coalescing, quest takeover and ambiguity/version fallback. Graphics, game data and model
loading are doubles: no GPU pixels, live bag interaction, native suppression, addon
annotation compatibility, protected execution or taint are established.

Source SHA-256 values for the installed 1.0.7 proof:

| File | SHA-256 |
| --- | --- |
| CallbackRegistry.lua | `dfdd8c015ec3eace26dc6921c25f4c2ee33e57babc778a4048bffc9875b6447f` |
| Tooltip_Base.lua | `aebc428f643b386e1db78f8e893a94b6854a3aa9ab8af26da47e40a4e1509b7d` |
| Tooltip_Private.lua | `f7e53b47834932fcb9942c437dd4b9d68658c1f98442a5405ef52e155278e1ff` |
| Tooltip_Public.lua | `50a5eec70914bb6c20cc3d18d102c52414fb08b2b38caded501439ebb2f6c805` |

The installed source is authoritative for this proof; upstream web snapshots may be
older. [Upstream tooltip sources](https://github.com/Peterodox/YUI-Dialogue/tree/main/Code/Tooltip)
and [callback registry](https://github.com/Peterodox/YUI-Dialogue/blob/main/Code/CallbackRegistry.lua)
provide navigation, not a compatibility promise. No source or assets are copied into
the toolkit; future redistribution of a modified Dialogue UI requires its own permission
review. The adapter would call the separately installed add-on in place.

# Equipment tooltips

## Intentions and settings

Use Dialogue UI's actual renderer for conventional equipment hovers, preserving public
native text and useful annotations. Do not recreate its artwork, typography or model
layout. The **Enhance equipment tooltips** checkbox and **Tooltip approach** dropdown
are account-wide and independent of comparison-footer cleanup:

- **Current UI + compact comparisons** retains Blizzard/ElvUI presentation and appends
  native replacement deltas. It has no custom model or skin.
- **Dialogue UI (original renderer)** uses installed Dialogue UI **1.0.7**. It supplies
  its own themed background, fonts, overlapping transparent model, camera, replacement
  section and Shift hint. The previous `dialogue` approximation preference migrates
  to this choice; the approximation's runtime code has been removed.

Missing/incompatible Dialogue UI keeps native presentation. **GameTooltip-driven**
non-equipped equipment hovers are the first supported path (normal bag items, and other
windows using that same tooltip). Equipped self-comparisons, combined/paired weapons,
override-item-level contexts and simultaneous ItemRef/custom windows retain native
presentation. Do not claim those contexts globally replaced before separate proof.
The native choice remains available for its compact combined-weapon summaries.

Disabling restores owned visuals. Existing compact text is removed through a native
rebuild outside combat; during combat, it disappears on the next natural rebuild.
`/pwttip` prints the selected approach, status, render/release counters and the last
sampled visibility/opacity. A delayed sample survives closing the hover to enter the
command; active=false by itself is normal after leaving the item.

## Ownership and implementation

`Comparison.lua` delegates the native choice's pairing/deltas to C_TooltipComparison.
Single-slot alternatives are labelled separately; combined/paired weapons use the
native API's paired arguments. Uncached, inaccessible and unknown data fall back.

`DialogueUI.lua` is a version-pinned internal adapter, not a new renderer. It discovers
the unique ordinary shared frame once per dependency version, then leases it only
while idle or already owned. Quest/tooltips from Dialogue UI take priority. A secure
SetOwner post-hook and OnHide observer release Phoenix ownership; stale cleanup never
hides a newer quest reward. No upvalue inspection, copied assets,
third-party source edits, global CVar changes or secure action hooks are used.

The adapter mirrors the **finished native tooltip's text**, colors, both columns and
inline texture markup after Show, including processors registered after Phoenix.
Semantic `lineIndex`/`price` data preserve native money rows through Dialogue UI's own
money formatter. `TooltipDataType.Item`, GUID, full link and level metadata are retained.
This is passed to the original ProcessTooltipData/Show methods; the native tooltip is
suppressed with owned alpha only after successful rendering. Original handlers,
comparison input, owner and data processing remain active. Comparison frames remain
native; the actual renderer anchors away from whichever side holds those comparisons.

During a lease, native data updates drive the mirrored body; Dialogue UI's duplicate
TOOLTIP_DATA_UPDATE subscription is removed. Shift still invokes the original renderer's
ReprocessInfo and preference; quest ownership naturally restores upstream event handling.
Repeated identical owner/text/color/price snapshots do not clear/reload the model or
restart its fade. A next-frame token allows clear/rebuild sequences to complete without
briefly releasing ownership. Equipment changes refresh the active comparison once.

No native fonts, backdrop or padding are restyled. The adapter retains other alpha
writers' public intent for restoration, but never drives replacement opacity from the
intentionally masked native tooltip. Show, SetShown and OnShow reapply suppression even
for cached/internal show paths without rebuilding the original renderer. It restores
native opacity on leave/disable/non-item transition. Restricted
frames/data use native fallback; protected restoration is deferred until safe. Errors
from protected actions are never swallowed.

## Limits and upgrade strategy

- Native text and inline icons are mirrored; arbitrary addon-created frames, interactive
  widgets, status bars or non-text overlays are not automatically transferred. Add-ons
  annotating both native and Dialogue UI surfaces may duplicate content and need a
  demonstrated, narrow adapter. Test ElvUI/ToxiUI and existing annotations explicitly.
- One upstream singleton cannot display two independent candidate tooltips at once.
  Sticky item links and competing contexts keep native fallback.
- The actual renderer retains its comparison preference and theme. Global hovers use
  its existing instant-show option; the configured quest-tooltip delay is unchanged. Model appearance variants/cameras need real-item acceptance. Combined
  weapon and override-level arithmetic are deliberately outside the initial reuse path.
- Before adding another version to the gate, rerun the source-backed fixture against
  that exact installed version, inspect ownership/event/model changes, and repeat the
  bag/quest/combat client trial. Never make a new version silently use a guessed frame.
- Future extensions should prefer AddItemTooltipProcessorExternal, scoped to an active
  owned lease and the callback's item identity. Keep Pawn's ProcessItemExternal hook intact.
  An upstream supported getter could replace discovery; no upstream message was sent.

[Research, source hashes and reuse rationale](research/README.md) records the boundary.

## Validation and first player test

```sh
python3 tests/run.py --lua /path/to/lua --dialogue-ui /path/to/AddOns/DialogueUI \
  --comparison-source /path/to/Blizzard/TooltipComparisonManager.lua
```

Fakes check native comparisons/fallbacks and settings. The source-backed proof executes
Dialogue UI's actual callback/base/private/public files plus Blizzard's constructor.
It covers native annotations/colors/money, original theme/fonts/model overhang/camera,
Shift, repeated rebuilds, external alpha, comparison-side placement, quest takeover,
non-item/unknown-version fallback, protected restoration and disable. This does not
prove GPU visuals, real combat/taint or source-window coverage.

After approved deployment and `/reload`:

1. `/pwt`: select **Dialogue UI (original renderer)**. Hover the same normal bag cloak
   or helmet for ten seconds. Expect the actual textured tooltip, overhanging model,
   original price/notes, one replacement section and no repeated flashing.
2. Switch items rapidly, press/release Shift, and check native side-by-side comparisons.
   Test current UI mode and disabled state: original presentation must return.
3. Keep bags open while hovering a Dialogue UI quest reward. It must retain its own
   tooltip; leaving the bag item must not hide the newer quest tooltip.
4. Test reload persistence, combat transitions, uncached items and BugSack. Equipped
   items and combined/paired weapons should use the documented native fallback.
5. If rendering differs, run `/pwttip` after the hover and capture its status. If the
   equipped item's native footer remains, run `/pwtcompare` and report the primary
   reason. Footer cleanup is independent and is not claimed fixed by this integration.

## Same-item preview refresh

The 1.0.7 adapter narrowly wraps DisplayModel to retain an already-loaded same-item
preview during Phoenix-owned text refreshes. All quest/unowned calls, different items
and forced equipment refreshes call the original function. This corrects the source-
backed annotation-refresh regression: updated text must not repeat TryOn. It is an
explicit exception to the post-hook-only approach, not a global model API override.
Native hide/show ownership resets remain a separate flicker path requiring validation.

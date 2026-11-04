# Universal item tooltips

## Intentions and settings

Enhance conventional equipment tooltips without discarding native/ElvUI item information
or other add-ons' annotations. **Enhance equipment tooltips** is enabled by default and
independent of comparison-footer cleanup. The account-wide **Tooltip approach** dropdown offers:

- **Current UI + compact comparisons**: retain Blizzard/ElvUI fonts and background,
  append native replacement deltas, and create no model preview.
- **Dialogue-inspired + embedded preview** (default): the same information with
  Blizzard's serif font, a dark background and a transparent model in reserved space
  at the tooltip's upper-right. Equipped comparison windows receive the typography,
  but never another summary or model.

Switching approaches or disabling restores owned fonts/background/padding. The disabled
checkbox restores the original tooltip presentation; the separate cleanup preference
can still hide the equipped item's redundant footer. During combat, existing appended
summary text changes on the next natural tooltip rebuild rather than a forced rebuild.

This is a native-tooltip presentation, **not Dialogue UI's renderer**. Its custom
artwork, exact layout, typeface and separate Shift hint are not reproduced. Native Shift
and always-compare controls still govern traditional side-by-side windows. We use no
Dialogue UI private API, code/assets or global CVar changes. Custom tooltips that bypass
Blizzard's item-processing system are outside the shared integration's coverage.

## Research and reuse decision

- [Dialogue UI public tooltip source](https://github.com/Peterodox/YUI-Dialogue/blob/main/Code/Tooltip/Tooltip_Public.lua)
  exposes annotation callbacks, not a global reward-tooltip renderer. Installed 1.0.6
  `Tooltip_Private.lua` owns its custom model/comparison machinery. The public callback
  registry even leaves RegisterCallback unexported. No applicable code/assets license
  grant was found in the bounded source/root inspection; nothing was copied.
- [Reward tooltip source](https://github.com/Peterodox/YUI-Dialogue/blob/main/Code/Dialogue/RewardTooltipCode.lua)
  is quest-context behavior, not a reusable global tooltip adapter. Replacing native
  bodies would also lose useful annotations and create context-specific integration.
- [AppearanceTooltip](https://github.com/kemayo/wow-appearancetooltip) is a maintained
  preview alternative with broad native-tooltip support. Its implementation also owns
  bindings, CVars, collection annotations and scene/position polling. No narrow public
  preview-provider API was identified. This task's smaller native DressUpModel view
  avoids adopting those unrelated behaviors. If AppearanceTooltip is installed, its
  preview owner wins and this feature does not create another preview.
- [Better Item Compare](https://www.curseforge.com/wow/addons/better-item-compare)
  advertises advanced weapon/stat comparison in native windows, but not this combined
  preview/inline experience; its publisher lists All Rights Reserved. It is a credible
  separate alternative, not a code dependency or code source here.
- Blizzard's [comparison APIs](https://github.com/Gethe/wow-ui-source/blob/live/Interface/AddOns/Blizzard_APIDocumentationGenerated/TooltipComparisonDocumentation.lua)
  own equipment pairing and signed/formatted deltas. Reuse those results rather than
  recomputing stats, sockets or specialization rules with GetItemStats.

## Implementation and limits

`Comparison.lua` builds groups from C_TooltipComparison. Single-slot alternatives
(rings/trinkets) are individually labelled; two-hand replacements pass both equipped
items to the native delta API. A bag-paired weapon explicitly names the paired item
and uses additive paired stats. Only the native first/default pair is summarized;
cycling another pair in Blizzard's side window does not silently change this named
summary. Item-level delta is shown only for unambiguous single-slot comparisons;
combined weapon item-level arithmetic is deliberately omitted.

`Feature.lua` registers one Item post-processor. It skips comparison windows, forbidden,
protected or secret-anchored tooltips, inaccessible data and unknown/uncached comparisons.
Existing body/annotations stay in place; data identity and tooltip-clear lifecycle
prevent duplicate sections. Hovering an equipped item with the same inventory link
has no replacement summary; an identical bag copy can also conservatively skip it.
Native tooltip rebuilds naturally retry when uncached data becomes available.

`Presentation.lua` changes individual native FontStrings, not shared FontObjects,
and retains per-region font snapshots. The native body, inline icons, money display,
item colors and annotation text are preserved. Other skins may still override the
background or append differently styled content; exact Dialogue UI parity is not claimed.

`Preview.lua` uses DressUpModel and the hovered link's transmog appearance/source camera.
Armor uses a masked player model; held items use their item appearance. The camera is
applied again after asynchronous model loading, and the transparent widget stays at
zero alpha until a model is ready. There is no bordered panel, independent anchor,
position polling or top/bottom window switching. Native right padding reserves text-free
space and participates in the normal comparison anchoring. Missing appearance/camera
information produces no preview or reserved column. Nonvisual items also have no model.
If AppearanceTooltip is installed, it remains the preview owner. Native tooltip rebuilds
retry uncached data. Actual camera framing still requires client validation.

Off hides owned previews, restores visual state and rebuilds visible owned native tooltips
outside combat. No protected comparison-display API, binding or global CVar is changed.

## Validation and player acceptance

`lua features/universal-item-tooltips/tests/test.lua .` checks native-delta delegation,
alternatives/pairs, self/uncached/unknown/secret fallbacks, original annotations,
preview ownership, asynchronous camera application, missing-camera fallback, font/padding
restoration, duplicate prevention, approach switching and native dropdown callbacks. It uses API fakes;
it does not establish real model rendering, source-window coverage or combat taint.

After approved deployment test a normal bag item first: original information plus
one correctly signed replacement group and its actual appearance preview. Then test
character equipment (no self comparison), bank/Warband bank, AH, vendor, loot and
links; ring/trinket alternatives, paired weapons and sockets. Check Shift/always compare,
uncached items, both independent switches, reload persistence, combat and BugSack.
Keep native fallback on any unsupported context; do not guess counterpart arithmetic.

For the next client trial, use the same cloak from the reported screenshot: confirm
there is no separate empty window above/below the tooltip, the armor preview appears
in the main tooltip's upper-right, and the original item body/annotations remain.
Switch both dropdown approaches on the same item, then disable enhancements completely.
Check font/padding restoration on a subsequent spell/unit tooltip and `/reload` persistence.
The screenshot exposed a real rendering gap despite the previous API-fake tests passing;
those tests are regression checks, not evidence of an acceptable in-game visual result.

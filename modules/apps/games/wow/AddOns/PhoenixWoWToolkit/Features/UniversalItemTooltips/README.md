# Universal item tooltips

## Intentions and delivered subset

Add compact replacement information and an equipment preview without discarding the
native/ElvUI item body or other add-ons' annotations. Default-on **Use Dialogue UI-style
item tooltips** is independent of comparison-footer cleanup. No Dialogue UI dependency,
private renderer access, source/assets copying or CVar changes.

This is a supported-API subset, **not Dialogue UI's renderer**. Native typography and
annotations remain; the preview is a small adjacent upper-right panel rather than an
embedded custom layout. Shift and always-compare still control Blizzard's traditional
side-by-side windows. The compact summary itself does not have Dialogue UI's separate
Shift toggle. These are deliberate presentation differences, not completed parity.

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

`Preview.lua` uses native DressUpModel/appearance cameras and the full hovered item
link, not a copied Dialogue UI model or artwork. Nonvisual items (rings/trinkets),
unsupported appearances and uncached models can have no preview. The model-loaded
callback uses current ownership and stops acting after clear/hide. Real equipment
camera framing and appearance fidelity still require client checks.

Off hides owned previews and rebuilds visible owned native tooltips outside combat.
During combat it waits for the next natural hover/rebuild to remove already-added
summary text. No protected comparison-display API, binding or global CVar is changed.
Broad coverage follows conventional Item tooltips; custom bag/AH renderers that bypass
that layer are not claimed supported without a demonstrated adapter need.

## Validation and player acceptance

`lua Features/UniversalItemTooltips/tests/test.lua .` checks native-delta delegation,
alternatives/pairs, self/uncached/unknown/secret fallbacks, original annotations,
preview ownership, duplicate prevention and toggle restoration. It uses API fakes;
it does not establish real model rendering, source-window coverage or combat taint.

After approved deployment test a normal bag item first: original information plus
one correctly signed replacement group and its actual appearance preview. Then test
character equipment (no self comparison), bank/Warband bank, AH, vendor, loot and
links; ring/trinket alternatives, paired weapons and sockets. Check Shift/always compare,
uncached items, both independent switches, reload persistence, combat and BugSack.
Keep native fallback on any unsupported context; do not guess counterpart arithmetic.

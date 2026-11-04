# Comparison footer cleanup

## Intentions and behavior

Default-on **Hide redundant comparison statistics** leaves native side-by-side
comparison and the equipped item's body/annotations intact. It is independent of
compact item tooltips and Dialogue UI. Disabling restores owned font visibility and
native dimensions immediately; enabling applies on the next natural comparison.

## Research and smallest viable adapter

Blizzard's [TooltipComparisonManager.lua](https://github.com/Gethe/wow-ui-source/blob/live/Interface/AddOns/Blizzard_SharedXMLGame/Tooltip/TooltipComparisonManager.lua)
appends its footer **after** `tooltip:ProcessInfo` has finished. Item post-processing
alone therefore cannot suppress it. No footer-specific native switch or removable
line API was found in this bounded source/API inspection. The manager directly adds
its blank row, localized introduction and API-produced delta rows. Better Item
Compare changes comparison presentation, but does not establish a native removal API.

The implementation uses secure post-hooks, not replacement methods or global delta
API overrides. A ProcessInfo observer records the equipped item's finished line count
and dimensions, including annotations already added by tooltip processors. The
SetItemTooltip observer recognizes only a structurally exact trailing native footer:

- The row count must equal the item body plus the native blank/header/delta rows.
- The introduction must equal Blizzard's current localized constant and the delta
  rows must exactly equal the native API's returned rows. This is validation against
  authoritative data, not English keyword/substring parsing or guessing stat lines.
- Blank/right-column rows must contain no unexpected annotations. Additional content
  or a changed layout makes the adapter leave the entire footer intact.

Only those tail font regions are hidden, and the pre-footer native body size is
restored. OnShow/OnSizeChanged enforce that view without polling. Original methods,
CompareHeader, item stats and comparison selection are untouched. When late appended
annotations alter the row count, previously trimmed regions are released and native
sizing wins. Hooks become inert when disabled.

## Conservative limits

Single comparisons (including ring/trinket alternatives) and WithBothHands are
recognized. Bag-paired weapon explanations and multi-pair cycling hints are retained
rather than hidden; their footer contains useful additional content beyond the simple
redundant paragraph. Unknown source shapes, inaccessible data, forbidden/protected
or secret-anchored tooltips are untouched. This is a narrow internal visual adapter,
not a claim that Blizzard exposes a supported footer-removal API.

Other add-ons replacing native footer rows or changing layout after our post-hook
may prevent cleanup. Do not broaden the match or truncate arbitrary lines to make
such cases appear supported. Reinspect current native source on Retail upgrades.
No CVar, input handler, protected display API or third-party files are changed.

## Validation

From the add-on root:

```sh
lua Features/ComparisonCleanup/tests/test.lua .
# Stronger optional source-backed proof:
lua Features/ComparisonCleanup/tests/test.lua . /path/TooltipComparisonManager.lua
```

The source-backed proof executes Blizzard's original SetItemTooltip. Tested source
SHA-256: `5734a4f0270f47b5d8c858d6f9d355d2850fc258687d75a372631369f3420727`.
Fixtures cover body/annotation preservation, exact footer matching, native size
refresh, disable/restore, extra/altered rows and independence from the compact feature.
All four enable/disable combinations also run with the compact feature on the same
processing path. The real-source proof caught and fixed a repeated-size-callback restoration bug:
retain the untrimmed dimensions when the callback observes our already-trimmed size.
No source is vendored and no running client is exercised.

After approved deployment, enable this alone first. Shift-hover a normal bag item:
side-by-side equipped information should remain, with no comparison paragraph or gap.
Toggle off to restore it, then combine with compact tooltips. Test annotations,
rings/trinkets, a two-hand replacement, paired/cycling fallbacks, repeated hovers,
reload, combat transitions and BugSack. Actual font geometry and ElvUI/ToxiUI behavior
remain in-game acceptance; local fakes do not prove taint safety.

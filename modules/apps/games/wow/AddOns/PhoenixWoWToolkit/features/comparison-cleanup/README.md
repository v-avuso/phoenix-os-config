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
including annotations already added by tooltip processors. The
SetItemTooltip observer recognizes only a structurally exact trailing native footer:

- The row count must equal the item body plus the native blank/header/delta rows.
- The introduction must equal Blizzard's current localized constant and the delta
  rows must exactly equal the native API's returned rows. This is validation against
  authoritative data, not English keyword/substring parsing or guessing stat lines.
- Blank/right-column rows must contain no unexpected visible annotations. Hidden pooled
  right-column text can retain stale values and is not treated as visible content. Additional content
  or a changed layout makes the adapter leave the entire footer intact.

Verified tail font regions are hidden immediately, independently of frame dimensions.
GetSize in a ProcessInfo hook may still describe the previous/full tooltip: the player's
`matched footer; waiting for native layout` diagnostic exposed that failure. Sizing
must never block suppression of already-recognized text.

Height is reclaimed from the first body's font inset, the verified spacer's top and
the last footer line's bottom, accounting for native extra top/bottom padding. Only
height changes; native width/layout remains authoritative. Missing or restricted line
geometry leaves the footer text hidden without guessing a crop. One next-frame retry
allows deferred geometry to settle, and normal size/show callbacks reapply the view.
Full footer geometry is retained for disable/restore.

OnShow/OnSizeChanged and secure post-hooks of Show and SetShown enforce that view without polling.
Calling Show on an already-visible tooltip can refresh text without another OnShow event
or size change; the post-hook reapplies suppression after that refresh. Original methods,
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
lua features/comparison-cleanup/tests/test.lua .
# Stronger optional source-backed proof:
lua features/comparison-cleanup/tests/test.lua . /path/TooltipComparisonManager.lua
```

The source-backed proof executes Blizzard's original SetItemTooltip. Tested source
SHA-256: `5734a4f0270f47b5d8c858d6f9d355d2850fc258687d75a372631369f3420727`.
Fixtures cover body/annotation preservation, exact footer matching, native size
refresh, disable/restore, extra/altered rows and independence from the compact feature.
All four enable/disable combinations also run with the compact feature on the same
processing path. Frozen GetSize snapshots, repeated stale body captures, missing/delayed
font geometry and internal SetShown visibility resets now have regressions. No source
is vendored and no running client is exercised.

After approved deployment, enable this alone first. Shift-hover a normal bag item:
side-by-side equipped information should remain, with no comparison paragraph or gap.
Toggle off to restore it, then combine with compact tooltips. Test annotations,
rings/trinkets, a two-hand replacement, paired/cycling fallbacks, repeated hovers,
reload, combat transitions and BugSack. Actual font geometry and ElvUI/ToxiUI behavior
remain in-game acceptance; local fakes do not prove taint safety.

The next player trial must repeat the reported bag-cloak hover with ElvUI/ToxiUI active.
Local regressions now cover repeated Show refreshing hidden text without an OnShow event,
and hidden pooled right-column strings with stale content. These address concrete gaps
in the old fixture; they do not establish which path caused the player's screenshot.
If the footer persists, retain the conservative annotation checks and inspect the actual
client's row/state layout rather than truncating arbitrary tooltip content.

## Live diagnostic

After hovering the failing item, run `/pwtcompare`. It reports enabled/available/running
state and the last primary/secondary guard result (baseline missing, row/header/delta
mismatch, restricted data, retained weapon/cycling context, or matched footer/layout
state), plus currently shown footer-font counts when a live comparison exists. No item
text, identifiers or personal data are printed. The observed size-gate failure has a
reproduction and correction; confirm actual rendering and spacing in the client. If
text remains, report the current guard/status and font visibility rather than assuming
a restart is needed.

## Independent visibility policy

**Manage comparison statistics** enables account-wide policy; **Hide comparison
statistics** selects Equipped item (default), Hovered item, Both or Neither. Equipped
suppression validates and hides only the exact native footer. Its FontString Show and
SetShown post-hooks reapply suppression if a later layout revives the matched regions;
changed text/annotations invalidate ownership. The Dialogue UI secondary body mirror
also receives the validated body-line limit rather than relying on native font visibility.

Hovered suppression controls Phoenix compact summaries and the original Dialogue UI
comparison section. With policy enabled, Dialogue UI's Shift hint is omitted and this
setting governs its summary without modifying upstream SavedVariables. Disabling policy
restores upstream behavior. The equipped-only choice leaves the hovered summary intact.

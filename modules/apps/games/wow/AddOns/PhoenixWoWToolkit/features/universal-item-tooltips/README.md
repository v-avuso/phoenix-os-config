# Item tooltips

## Intentions and settings

Reuse installed Dialogue UI's actual text renderer, theme and model preview while
preserving native item information and useful annotations. Do not copy its assets or
replace secure input. Account-wide controls under `/pwt`:

- **Customize item tooltips** enables this feature.
- **Tooltip framing style** independently chooses Dialogue UI or Default backgrounds.
  Applied to observed native tooltips and the original Dialogue UI tooltip, including
  its quest rewards. Default uses the available native backdrop or Blizzard fallback;
  custom ElvUI skin widgets cannot be cloned automatically.
- **Tooltip content style** chooses Dialogue UI or Default item text/layout. Default
  retains native information and adds compact native replacement deltas. Dialogue UI
  uses the original item renderer, including its overlapping transparent model when
  available. Items without a model use the same typography/layout.

Comparison visibility is independently owned by [Comparison Cleanup](../comparison-cleanup/README.md).
Its enabled policy controls summaries globally and removes Dialogue UI's Shift hint;
no comparison CVar or Dialogue UI saved preference is changed. Disabling that policy
restores upstream comparison preferences. Existing content preference keys migrate
without resetting account settings.

## Implementation and boundaries

`Comparison.lua` delegates pairing and deltas to native C_TooltipComparison APIs.
`DialogueUI.lua` gates internal reuse to Dialogue UI **1.0.7**, discovering its unique
ordinary shared frame once. It leases the singleton for GameTooltip item hovers;
Dialogue UI quest ownership takes priority. Native frames keep their original data,
owner, processing and input, with alpha masked only after successful replacement.
Finished public text, both columns, colors, inline icons and semantic price rows are
mirrored, preserving native addon annotations. No third-party files are modified.

Same-item text refreshes retain the loaded model through a narrow DisplayModel
wrapper. Native clear/hide/rebuild/show sequences are coalesced until the next frame:
a successful render invalidates pending release; a genuine leave releases ownership.
This specifically covers a refresh path seen in bags; bank stability alone does not
establish that every inventory refresh path is fixed.

`Style.lua` applies/restores owned backgrounds. Secondary item/comparison panes use
separate ordinary frames with an explicit whitelist of upstream **self-based base
text/layout methods**. Singleton model, comparison, event and hotkey closures are not
cloned. The base methods are captured before upstream initialization removes its
initializer; if unavailable, secondary panes fall back to native content. These panes
omit the cleanup adapter's validated native footer and preserve other text. Only the
main hovered item uses the upstream singleton model. Comparison panes chain against
the actual rendered neighbor, rather than the smaller native anchor. When their total
width exceeds space beside the hovered item, equipped panes scale down together to
fit; native frames and the hovered item remain unchanged.

No private source or artwork is copied. [Research](research/README.md) records the
installed source and reuse decision. This remains a version-pinned internal adapter,
not an upstream supported global renderer API.

## Limits and upgrades

- Content replacement targets conventional public item tooltips. Unit/spell content
  stays native; its framing can still be styled. Arbitrary interactive addon widgets,
  status bars and custom overlays are not transferred.
- Combined/paired weapon arithmetic, override-level contexts and busy singleton
  ownership retain native fallback. Multiple comparison panes and custom skin geometry
  require client testing; this is not a guarantee of universal pixel-identical output.
- Forbidden/protected frames and inaccessible/secret data are skipped. Protected
  restoration is deferred until safe. No swallowed protected-action errors or CVar changes.
- On disable, owned alpha/backgrounds restore. Native appended summary text disappears
  on a safe rebuild or next natural rebuild in combat.
- Before accepting another Dialogue UI version, inspect ownership/model/base changes,
  rerun the source-backed fixture against that exact version, and repeat live tests.

## Validation

From the add-on root:

```sh
python3 tests/run.py --lua /path/to/lua --dialogue-ui /path/to/AddOns/DialogueUI \
  --comparison-source /path/to/Blizzard/TooltipComparisonManager.lua
```

The fixture executes unmodified upstream callback/base/private/public files and
Blizzard's comparison constructor. Checks include annotations/money, model cameras,
same-item text refreshes, transient hide/show, true leaves, alpha restoration,
comparison bodies, no-model items, independent framing/content settings and policy,
quest takeover, version fallback and protected restoration. Fakes do not prove pixels,
combat taint or real window coverage.

After deployment and `/reload`, test a steady bag hover against the same bank item;
rapidly switch items and check both comparison panes. Test no-model items, character
sheet, merchant/AH and quest rewards; all four framing/content combinations; each
comparison visibility choice and disabled settings; reload persistence; combat and
BugSack. Use `/pwttip` and `/pwtcompare` after a failing hover. A restart does not
install checkout changes: the immutable package must be deployed first.

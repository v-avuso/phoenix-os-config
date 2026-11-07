# Item tooltips

## Intentions and settings

Reuse installed Dialogue UI's actual text renderer, theme and model preview while
preserving native item information and useful annotations. Do not copy its assets or
replace secure input. Account-wide controls under `/pwt` → **Tooltip**:

- **Customize tooltips** enables this feature.
- **Tooltip framing style** independently chooses Dialogue UI or Default backgrounds.
  Applied to observed native tooltips and the original Dialogue UI tooltip, including
  its quest rewards. **Default is the initial choice**: native tooltips keep their
  existing skin, and replacement content delegates its background to ElvUI when
  available (otherwise uses the native backdrop or Blizzard fallback). Existing saved
  framing choices are preserved; select Default to adopt this on an existing account.
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
text/layout methods**. Singleton comparison, event and hotkey closures are not cloned. The base methods are captured before upstream initialization removes its
initializer; if unavailable, secondary panes fall back to native content. These panes
omit the cleanup adapter's validated native footer and preserve other text. Each pane
initializes its own preview with the upstream self-based initializer and display
method, captured before initialization. Cameras, transmog setup, overlapping model
placement and creature animation remain upstream-owned. Same-item text updates reuse
the loaded model; different items and reopened panes run the original display method. Comparison panes chain against
the actual rendered neighbor, rather than the smaller native anchor. When their total
width exceeds space beside the hovered item, equipped panes scale down together to
fit; native frames and the hovered item remain unchanged.

No private source or artwork is copied. [Research](research/README.md) records the
installed source and reuse decision. This remains a version-pinned internal adapter,
not an upstream supported global renderer API.

## Limits and upgrades

- Content replacement targets conventional public item tooltips and resolved native
  mount/pet summon tooltips. Other unit/spell content stays native; framing can still
  be styled. Arbitrary interactive addon widgets,
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

## Equipped, mount and pet previews

With Dialogue UI content enabled, equipped comparison panes display independent
previews when the item has an appearance. Rings/trinkets typically have no wearable
model, so those panes remain text-only. Existing width fitting includes preview layout.
The **Show equipped-item previews** checkbox controls these independently; content
style must be Dialogue UI. Turning it off preserves the equipped item's text.

Dialogue UI already resolves mount items through C_MountJournal and pet items through
C_PetJournal.GetPetInfoByItemID. Its original creature display, idle animation and
turntable provide animated rotating previews without a custom animation loop. Only
visible preview models use upstream OnUpdate animation; no tooltip polling is added.
Unsupported item appearances fall back to text. Summon tooltip support is described below. Caged battle-pet links and custom widgets
outside the native tooltip-data path still need a separate adapter.

Client acceptance: compare two wearable armor/weapon items and verify both previews,
then hover mount and pet items. Confirm rotation, switching item types, repeated text
refreshes, disabling content customization, and quest-reward ownership. Source-backed
fixtures prove separate model ownership, no repeated dressing on text refresh, native
creature display/animation and turntable updates; they cannot prove real creature
framing or GPU appearance.

## Creature overflow and summon tooltips

The Tooltip page contains four independent, default-on preview checkboxes:

- **Show equipped-item previews**: retain/hide available equipped appearances.
- **Allow creature previews to overflow**: enlarge the creature model's physical
  clipping viewport to three times its logical width/height. Matching positive view
  insets keep the original projection rectangle; the original center, layout space,
  camera and model scale remain unchanged. Disabling restores original viewport and
  zero insets. This is bounded extra space, not unlimited rendering outside a GPU
  viewport. Pixel-size preservation and oversized mounts require in-game acceptance.
- **Show mount summon previews**: resolve public Spell/Mount data or
  SetMountBySpellID identities through C_MountJournal.GetMountFromSpell and the mount's
  native display data. Mirror finished tooltip text on an independent upstream view.
- **Show pet summon previews**: use the native CompanionPet GUID or SetCompanionPet
  setter argument and C_PetJournal.GetPetInfoByPetID's display ID. No name matching,
  guessed summon spell mappings, journal filter changes or pet summoning is used.

Preview options require Dialogue UI content. Generic combat spells, random-summon
buttons without a definite creature, secret/restricted identities and unsupported
custom tooltips retain native presentation. Native action buttons using the standard
summon tooltip paths are covered by the adapter; exact OPie/journal/action-bar coverage
requires a live check. Caged battle-pet links are still outside this path.

`Preview.lua` owns identity resolution, creature-model setup through the upstream
preview object, and reversible viewport expansion. Hooks are passive, data-driven and
installed before the first native setter call. Native text/annotations remain active;
owned alpha restores before switching between summon and item renderers. No polling,
input changes or CVar edits are introduced. Upstream turntable OnUpdate remains solely
for visible model animation.

Client test: hover a previously clipped large mount with overflow on/off, checking
that apparent size and center stay unchanged while more of the creature is visible.
Try mount summon buttons/spell links and pet summon buttons; toggle both options
separately, switch back to an item/combat spell, enter/leave combat and reload.
Verify tooltip annotations, no flicker, settings persistence, and General/Tooltip
navigation. Lua fakes verify viewport/projection arguments, restoration, summon
identity, stale-identity rejection and ownership transitions; they do not prove GPU
projection, clipping or combat taint.

## Model compositing, action bars and native skins

Raising ordinary layers did not resolve the player's journal masking screenshot.
Independent Phoenix Model1 widgets now enable an isolated framebuffer once at creation,
following the installed Leatrix Plus viewer's remedy for background-model silhouettes.
It stays initialized while hidden: toggling it off can leave existing models blank.
Borrowed Dialogue UI singleton and journal models are untouched. Ordinary foreground
levels/draw layers still restore on disable. GPU composition needs client acceptance.

A passive SetAction post-hook resolves public action metadata. Spell actions and Retail
macro subtype spell use their resolved spell ID; macro indexes use GetMacroSpell.
When that does not resolve a spell, the native tooltip's GetSpell supplies its public
identity. Opaque mount indexes are never interpreted as spell IDs. Summonpet actions
supply a pet GUID. No action attributes, buttons, macro text or bindings are modified.
Missing/secret identities and item macros retain native fallback.

Dialogue UI framing suppresses the native backdrop and the known iborder, oborder,
NineSlice and Background surfaces, plus ToxiUI's txSoftShadow, txInnerShadow and
txInnerNoise decorations. Late alpha/show/backdrop/template resets cannot revive a
second visible skin. Default framing or disabling restores the latest native intent;
annotations, status bars and other children remain intact.

`/pwttip` prints `framing-v3` and the last public action-resolution route, surviving
leaving the button. Development deployments use phoenix-test, then `/reload`; restart
is not a remedy for a verified runtime failure and the next-boot profile stays intact.
Client test: check the marker, overlap journal models, hover a dragged mount and macro
on the action bar, and switch framing on unit/spell/item tooltips. Test overflow on/off,
reload, modifiers and combat. Fakes verify adapter calls/restoration, not GPU output.

## Uniform framing for units, auras and WunderBar

The existing **Tooltip framing style** setting controls conventional action, unit,
aura/buff, item and WunderBar tooltips. Framing is independent of content replacement:
unit and buff information remains native. Missing/restricted tooltip data does not
prevent styling an otherwise safe frame; protected, forbidden or secret-anchored
frames still fall back without relaxing their access boundary.

Style.lua observes named GameTooltip, ItemRefTooltip, shopping tooltips and ElvUI's
DataTextTooltip, including ordinary Show calls without data callbacks. WunderBar's
inspected Profession/SpecSwitch/Currency modules use that shared DataTextTooltip.
Discovery repeats at login/entering world and relevant addon loads, not by polling.
Native unit/aura setters also receive passive skin post-hooks, because they can reset
appearance internally while the tooltip remains shown. Their arguments are ignored.

Only selected skin surfaces are suppressed. Text, status bars, annotations, input
and anchoring are retained. Source-backed fixtures cover native Background visibility,
late NineSlice resets, raw DataTextTooltip, restricted aura content, setter resets,
Default restoration and protected-anchor fallback. Client test: select Dialogue UI,
hover the player, a buff, an action button and WunderBar; expect one textured frame
without the native thin outline. Switch to Default and back, then disable customization.
Check annotations, combat and reload. `/pwttip` prints revision `framing-v3`; actual
ElvUI/ToxiUI visual uniformity still requires player acceptance.

ToxiUI Theme.SetTemplate adds three separate decorations after ElvUI's template call;
clearing the native backdrop alone does not remove them. A coalesced next-frame
refresh after native backdrop changes lets the provider finish colors/decorations
before suppression. No inherited SetTemplate method is shadowed or globally patched.
Default framing restores recorded decoration alpha and the latest public color intent.

The native default-anchor hook discovers alternate ordinary GameTooltip frames,
including the cooldown viewer's GetAppropriateTooltip path, before their data setter
runs. Protected/forbidden/secret-anchored tooltips remain untouched. After hovering a
buff/cooldown that still looks native, run `/pwttip`: the **PWT framing** line records
the last frame, setter route and applied/skipped reason without recording aura text,
unit names, IDs or coordinates. Such a runtime skip is a compatibility limit to
investigate, not evidence that a restart or another layer adjustment is needed.

## Compatibility and background ownership

Dialogue UI 1.0.7 and 1.0.7 b are explicitly accepted. The four inspected tooltip and
callback files have identical hashes in these releases. Other versions remain native
until inspected; `/pwttip` includes the full installed version. The upstream-backed
test reads the entire TOC version line, including suffixes, so its metadata matches
the actual client rather than silently dropping the suffix.

Default framing leaves native tooltip providers alone. For our replacement content,
ElvUI Tooltip:SetStyle constructs the background on an owned ordinary frame, allowing
ToxiUI's existing SetTemplate hooks to supply their own decoration. No provider methods
are overridden. This avoids cloning skin widgets and does not change content/previews.
The provider call has a fixture; final colors, borders and combat behavior require WoW.

The optional Dialogue UI framing mode still uses the earlier observed-frame adapter;
its reported border inconsistency is not claimed fixed by this compatibility repair.
See research for the supported aura path before extending that mode.

# Actual Dialogue UI reuse boundary

## Intentions and decision

Reuse the separately installed renderer and its assets in place. A missing supported
export is not proof that reuse is impossible. Do not extend the former native-tooltip
imitation or clone singleton-bound methods onto another frame. The selected integration is
owned by [DialogueUI.lua](../DialogueUI.lua); [feature usage and acceptance](../README.md)
owns current behavior. Source proof is not client visual/combat acceptance.

## Findings from installed Dialogue UI 1.0.7

- Tooltip_Base creates theme-owned background, DUIFont objects and layout. Tooltip_Private
  augments **one shared instance** with model/camera, deltas, hotkey hint and events.
- AddItemTooltipProcessorExternal is public and passes that actual instance to item
  callbacks. It supports future annotations but cannot acquire the renderer immediately
  before the first Dialogue UI item tooltip. The callback is queued: check current
  owner and item identity before applying an extension.
- TooltipSetHyperLink's registration API is commented out in CallbackRegistry. Its
  object getter creates only a base tooltip, not the private preview/comparison renderer.
- No global renderer/namespace export was found. A read-only EnumerateFrames scan can
  identify the unique ordinary shared frame by its combined method signature before
  first use. Gate to the inspected version; reject ambiguity/protection. This is an
  internal compatibility adapter, not an upstream-stable API.
- The public item callback corroborates the discovered identity. SetOwner/OnHide hooks
  preserve upstream ownership. No upstream source or assets are redistributed.

## Data dispatch and preservation

SetHyperlink derives isItem by searching its getter name for `Item`; `GetHyperlink`
does not match. Forwarding a link through that accessor therefore misses comparison
and item-processor behavior. ProcessInfo with an explicit isItem flag works, but obtains
a fresh C_TooltipInfo body that omits native post-processor annotations.

The production path instead mirrors the final native public rows and calls the original
ProcessTooltipData with isItem=true. It also retains `type=Enum.TooltipDataType.Item`:
Blizzard's real CreateComparisonItem constructor requires that separate type metadata.
The constructor-backed regression caught the distinction that a permissive fake missed.
Native semantic lineIndex/price values preserve money formatting without localized
string matching. Arbitrary child widgets are not text and need separate compatibility
proof; addons annotating both surfaces may produce duplicates.

## Singleton, refresh and appearance

The original Shift handler and some update callbacks close over SharedTooltip, so a
shallow method clone is not an independent renderer. One shared instance must have one
owner. A lease yields to quest ownership; stale source cleanup cannot hide a newer
quest reward. Concurrent sticky links retain native fallback.

The actual preview's Y offset is `0.33 * modelHeight`, producing the reference overhang.
Its own source camera applies after model loading. It also uses its own theme, fonts
and show delay (the main Dialogue UI frame configures 250 ms). Global hovers use its
existing Show(true) argument to appear immediately without changing the quest delay.
The hidden native tooltip's alpha is not a replacement-view fade source; native show
resets must be masked again on cached and internal show paths. None of the renderer's
artwork or model code needs copying.
The original model resolves appearance information from item ID internally; appearance
variants need real-item checks before a scoped full-link extension is justified.

Fresh native data tables can describe one unchanged hover. Compare owner, text, colors
and price rather than table identity; do not hide/reload the model or restart the fade
every postcall. While leased, the native source drives updates and the duplicate upstream
data subscription is removed. Original Shift reprocessing still works. An item change,
real text change or equipment event can trigger a new render.

## Comparison correctness and future extensions

The renderer's comparison preference remains DialogueUI_DB.TooltipShowItemComparison.
Do not install a competing Shift controller or silently overwrite that preference.
Keep ProcessItemExternal intact: Pawn already uses it.

Upstream AddComparisonItems calls the delta API per equipped item without the paired
arguments used by Blizzard's combined comparison path. Its own item-level formatter
also works from links, rather than an override-level context. The initial adapter
therefore keeps equipped self-comparisons, combined/paired and override-level contexts
native. Do not claim those semantics proven by a single-slot bag-item trial.

Prefer future extensions through the public annotation callback, conditional on an
active owned lease and the callback item identity. A supported upstream getter/render
entry point is the best long-term replacement for discovery; no upstream issue or
message was sent. An independent factory would need to untangle singleton callbacks
and is justified only by demonstrated concurrent-tooltip needs. A fork or a new renderer
is unnecessary for the primary workflow and adds permission/maintenance burdens.

Equipped-footer cleanup is owned by the comparison feature. The player accepted the
suffix-validation and rendered-pane-spacing correction before this preview extension.
Use `/pwtcompare` and an exact-source regression for any new footer failure; renderer
reuse by itself does not prove cleanup.

## Evidence and limits

`tests/dialogue-ui.lua` executes installed, unchanged CallbackRegistry, Tooltip_Base,
Tooltip_Private and Tooltip_Public files through the actual runtime adapter. When
supplied, the original Blizzard constructor is also executed. Graphics, source game data
and model loading are doubles. No GPU pixels, native window coverage, arbitrary widgets,
combat/taint or live quest handoff are established; use the owning README's client trial.

Source SHA-256 values for the installed 1.0.7 proof:

| File | SHA-256 |
| --- | --- |
| CallbackRegistry.lua | `dfdd8c015ec3eace26dc6921c25f4c2ee33e57babc778a4048bffc9875b6447f` |
| Tooltip_Base.lua | `aebc428f643b386e1db78f8e893a94b6854a3aa9ab8af26da47e40a4e1509b7d` |
| Tooltip_Private.lua | `f7e53b47834932fcb9942c437dd4b9d68658c1f98442a5405ef52e155278e1ff` |
| Tooltip_Public.lua | `50a5eec70914bb6c20cc3d18d102c52414fb08b2b38caded501439ebb2f6c805` |

Installed source is authoritative for this proof; upstream web snapshots may be older.
[Upstream tooltip sources](https://github.com/Peterodox/YUI-Dialogue/tree/main/Code/Tooltip)
and [callback registry](https://github.com/Peterodox/YUI-Dialogue/blob/main/Code/CallbackRegistry.lua)
provide navigation, not a compatibility promise. No copying/forking license is assumed;
redistributing a modified Dialogue UI would require its own permission review.

## Independent preview reuse

In inspected 1.0.7, SharedTooltip.Init, GetHyperlink, GetItemID and DisplayModel use
self; their preview model initialization and callbacks likewise use the owning model
instance. Unlike ShowItemComparison and OnEvent, these methods do not close over the
shared tooltip. The adapter therefore captures those function references before Init
removes InitFrame and invokes them on independently allocated comparison views. No
source/assets are copied. Each view owns its PreviewFrame, DressUpModel and ModelScene.
The existing base Show/Layout applies the original preview spacing and alpha.

DisplayModel already resolves mount items with C_MountJournal.GetMountFromItem and
pet items with C_PetJournal.GetPetInfoByItemID, then selects creature display, idle
animation and SetUseTurntable(true). Reusing that path is cheaper than adding another
model addon or duplicating camera/rotation code. Native summon tooltips lack ordinary
item identity; the adapter below supplies a resolved creature directly, without
converting it to a guessed item. Custom journal widgets and caged battlepet links
remain separate contexts.

## Native summon identities and expanded viewport

Blizzard's [MountJournal API](https://raw.githubusercontent.com/Gethe/wow-ui-source/live/Interface/AddOns/Blizzard_APIDocumentationGenerated/MountJournalDocumentation.lua)
provides GetMountFromSpell. [TooltipInfo](https://raw.githubusercontent.com/Gethe/wow-ui-source/live/Interface/AddOns/Blizzard_APIDocumentationGenerated/TooltipInfoDocumentation.lua)
provides GetCompanionPet(petGUID), and native SetCompanionPet carries that same identity.
Installed Plumber's summon flyout likewise uses SetCompanionPet for owned pet GUIDs;
no reliable generic pet-spell-to-species mapping was established, so none is guessed.

The native [SimpleModel API](https://raw.githubusercontent.com/Gethe/wow-ui-source/live/Interface/AddOns/Blizzard_APIDocumentationGenerated/SimpleModelAPIDocumentation.lua)
provides SetViewInsets. Installed Narcissus ProductList documents that insets affect
projection without enlarging the clipping viewport. The bounded prototype therefore
enlarges the physical widget, centers it over its original rectangle and applies
matching insets, retaining logical layout dimensions. This is an API-argument proof;
unchanged apparent size and actual clipping improvement remain GPU/client acceptance.
No model scale/camera change is substituted for the requested same-size overflow.

## Action-bar identity and model ordering

Blizzard's [ActionButton SetTooltip](https://raw.githubusercontent.com/Gethe/wow-ui-source/live/Interface/AddOns/Blizzard_ActionBar/Shared/ActionButton.lua)
uses GameTooltip:SetAction, unlike the journal's SetMountBySpellID. The installed
ElvUI_Libraries LibActionButton Action.GetSpellId confirms current GetActionInfo
semantics: spell actions and macro subtype spell already return the spell ID;
untyped macro indexes require GetMacroSpell. The adapter follows these native
identities and never parses secure macro text or action attributes.

Inspected Dialogue UI initializes its model frames at the parent tooltip's level,
and Model1 uses ARTWORK. The foreground prototype changes those ordinary rendering
properties with exact restoration. The native SimpleModel API documents OVERLAY as a
model draw layer but does not prove that layers isolate 3D depth composition. The
reported journal masking requires a client test. SetUseGBuffer is restriction-marked
in native documentation; no speculative restricted call or swallowed error is used.

## Evidence after the foreground trial

Player screenshot after verified installation/reload still showed the journal dragon
masking the tooltip bear. Ordinary frame/draw layering was therefore insufficient in
that trial; a restart was not indicated. Installed Leatrix_Plus.lua's model viewer
initialization explicitly documents the same silhouette interaction and enables
SetIsFrameBuffer(true) once. The native Frame API exposes SetIsFrameBuffer(bool) with
non-secret arguments; it is distinct from restriction-marked Model:SetUseGBuffer.
The Phoenix experiment applies it only to owned Model1 widgets, preserving borrowed
models and avoiding the documented off-toggle blank-model problem.

Installed ElvUI Toolkit.SetTemplate creates iborder/oborder as ordinary child frames.
Clearing SetBackdrop does not clear those frames. The adapter now owns their alpha
only while Dialogue UI framing is selected, with restoration and late-write tests.
The action path additionally accepts a public tooltip GetSpell identity rather than
interpreting an opaque mount action index; runtime diagnostics record the actual route.

## Native/raw tooltip framing coverage

Blizzard TooltipDataHandler.InternalProcessInfo runs tooltip postcalls, then Show,
then optional SharedTooltip_SetBackdropStyle. Appearance can therefore reset after
an all-types callback. The adapter suppresses known native skin surfaces with guarded
alpha/show hooks and passive unit/aura setter post-hooks, without reading aura args.

Installed ElvUI DataTexts/DataTexts.lua creates the named DataTextTooltip at file load.
ToxiUI WunderBar Profession/SpecSwitch/Currency add raw lines to DT.tooltip and Show it;
there need not be an item/spell data callback. Explicit named-frame observation reuses
this existing frame and preserves its content, with lifecycle-based late discovery.
The earlier framing code also left native Background visible and did not guard late
NineSlice resets. Regressions now distinguish those skin surfaces from the selected
texture and verify Default restoration. Secret data is not inspected; the original
protected/forbidden/anchoring checks remain in force.

## ToxiUI decorations and alternate aura/cooldown frames

The next player trial still showed a dark outline despite native skin suppression.
Installed ToxiUI Modules/AddOns/Theme.lua:SetTemplate and Core/Functions/Core.lua
identify three omitted surfaces: txSoftShadow (ordinary frame), txInnerShadow and
txInnerNoise (textures). These are separate from the native/ElvUI backdrop and may
be created after SetBackdrop callbacks. The adapter now suppresses those known
surfaces after a coalesced native-backdrop refresh, with Default restoration regressions.
The callback lets provider colors/decorations finish; it does not cache or shadow the
inherited, dynamically hooked SetTemplate method. Explicit public color arguments
are retained for restoration even while the displayed native backdrop is suppressed.

Blizzard CooldownViewerItemDataMixin:OnEnter chooses GetAppropriateTooltip, calls the
native default anchor, then sets an aura-instance or spell tooltip. Passive discovery
at GameTooltip_SetDefaultAnchor handles alternate ordinary tooltips without guessing
names or querying aura arguments. Tests cover that flow and target-aura setters.
Runtime diagnostics now record the exact frame/route and access-gating result; they
must establish any remaining blocked native aura context before further changes.

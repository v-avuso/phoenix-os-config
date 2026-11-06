# Combat Tracking — experimental client trial

## Intentions

Make Druid procs and player-applied DoTs recognizable at a glance, while preserving
threat, healing-frame indicators, secure combat boundaries and other add-ons' profiles.
This is a prepared first client trial, **not verified combat functionality**. Do not
expand integrations until the two-buff fallback and two-debuff combination pass below.

## Use

Open `/pwt` → **General → Combat Tracking**. Enabled by default for Druids only.
Profiles select automatically by specialization. Choose Global, Druid or specialization
overrides in the editor. Scalar settings inherit; editing a list replaces that list
at the selected scope. **Reset to inherited** removes that scope's overrides, returning
specializations to their preset plus inherited presentation settings.

Enter numeric fields with **Enter**. Changes persist immediately account-wide in
`PhoenixWoWToolkitDB.features.combatTracking`; **Apply changes** rebuilds the displays.
Applying or disabling in combat queues the change until combat ends. Spec/talent
events also apply saved changes outside combat. Existing combat displays remain until
queued configuration is applied. `/pwtcombat` reports configuration/slot counts only;
it never samples live aura state.

For an isolated renderer test, `/pwtcombat test` outside combat creates a temporary
bar above the configured position: Barkskin `22812` takes priority over Mark of the
Wild `1126`. Cast Mark, then Barkskin; check fallback when Barkskin ends. This does
not change saved preferences. `/pwtcombat stop` removes the test outside combat;
disabling the feature also removes it, with the normal combat deferral.

Bars accept any number of enabled candidates with Up/Down priorities. Use the **aura**
spell ID, which can differ from the cast ID. Invalid/unavailable IDs are skipped by
rendering; an unavailable talent simply never matches. ID validation confirms the
client recognizes a spell, **not** that it is learned or exposed as a trackable buff.
The first editor uses explicit IDs rather than guessing cast-to-aura mappings from
the spellbook. Every bar can override size, offsets, texture, fill opacity, icon and
label. Guardian defaults to a 65 × 6 cyan/orange stick without icon or label, anchored
beneath `ElvUF_Player.Power` using the existing ElvUI/ToxiUI texture. Other bars use
the shared screen-center position. The per-bar anchor checkbox selects this behavior;
without ElvUI the shared position is the fallback. Anchoring changes no resource bar.
Blank per-bar
numbers inherit shared settings, except vertical offset which defaults to stacking.

Nameplate highlights accept up to three player-applied debuffs. Borders use the mean
RGB of every active effect. Health bars, threat colors and provider profiles are never
changed. Health tinting is deliberately absent from this trial to keep threat clear.
Color swatches update immediately; palette S/V defaults to 75%/95%. Adding an effect
selects the most separated suggested hue. Hue edits clear a hex override; a valid
six-digit hex override remains independent of global S/V. Empty hex restores palette.

## Presets and unresolved aura identity checks

| Spec | Bar priority | Nameplates |
|---|---|---|
| Guardian | Incarnation: Guardian of Ursoc `102558` (cyan) → Dream Conduit `1308176` (orange) | Moonfire `164812` |
| Balance | Solar Eclipse `48517` → Lunar Eclipse `48518` | Moonfire `164812` + Sunfire `164815` |
| Restoration | Clearcasting `16870` → Soul of the Forest `114108` | Inherited Moonfire |
| Feral | No spec bar | Inherited Moonfire only |

The installed Retail client metadata is `12.1.5.70783`; installed ToxiUI is `7.6.1`
and ElvUI's declared requirement is `15.26`. Spell catalog entries were researched,
but the character's spellbook/talent state and actual aura matches require client
validation. The player has observed Dream Conduit in the initial client trial;
Incarnation matching and the revised nameplate adapter still need client acceptance.
The Guardian preset now follows Incarnation rather than the earlier hidden Answered
Calling proposal. There are no inferred timers. Ascendant Eclipses is a passive apex
talent, not an assumed active buff; extra Ascendant state IDs are deferred until
verified. No Astral Power bar is added.

ElvUI's Mainline `AuraWatch` defaults already include Rejuvenation, Lifebloom,
Regrowth, Wild Growth and Germination. No healing-frame changes are made. Whether
these indicators are enabled in the user's current profile needs an in-game check;
the private profile was not changed or treated as portable configuration.

## Reuse and secure design

- `Model.lua`: presets, isolated profile copies/inheritance, HSV/hex and subset colors.
- `Display.lua`: thin adapter to `CustomAuraContainerTemplate:AddAuraSlot`, native
  `SetIcon`, `SetSpellName` and `SetDurationBar`. Blizzard owns aura assignment,
  visibility, duration objects and progress. No `UNIT_AURA` handler, aura scanner,
  visibility query, secret-value comparison, secure input hook or combat polling.
- `Feature.lua`: Druid/spec lifecycle, queued configuration, public nameplate anchors,
  recycled nameplate displays and diagnostics. Unchanged configuration events do
  not allocate displays. Explicit changed configurations create a fresh tree; WoW
  retains frame allocations until reload, so repeatedly applying different layouts
  is not a steady-state performance benchmark.
- `Options.lua`: feature-owned editor using the toolkit's existing native canvas.
  No core framework or Nix deployment changes are required.

Native slots accept identity filters but expose only predefined sort comparators.
For custom priority, equal-sized independent slots overlap with higher priority at
higher frame levels. An opaque backing covers **all** lower-priority pixels. Opacity
therefore controls the fill, not the complete composited bar; transparent backing
would leak lower-priority text/progress. Only the highest active effect is visually
present; secure slots underneath continue to update normally.

Composite borders use parent visibility as AND: a two-effect rule has a container
and slot for each condition, nested during `initializeFrame`. Children are configured
before Blizzard applies access restrictions to the outer slot. The final slot draws
the border. More specific combinations cover singleton borders. Three effects cost
seven rules / twelve slots per plate; two cost three rules / four slots. This is
linear in visible plates, with no pooled-aura permutation explosion. Nesting and
frame-level composition are **source-supported hypotheses pending client proof**.
If the trial produces a forbidden-action error, stop that component; do not bypass
access restrictions or infer state through hooks.

ToxiUI's native cooldown viewer integration already owns its layout, gradients and
class/power bar choices. Its gradient is class-wide, not per-effect priority. PWT
reads the existing ElvUI texture/font where available, without replacing that theme
or modifying ToxiUI's database. The native viewer remains usable independently;
disable PWT's duplicate proc bar if the native display already suffices.

Plater documents `C_NamePlate.GetNamePlateForUnit(unit).unitFrame.healthBar` as an
attachment point. ElvUI uses `unitFrame.Health`; Blizzard's `UnitFrame.healthBar`
is another fallback. Unknown, forbidden
or protected anchors are skipped. Plater is optional and was **not found in the
configured local AddOns directory** during this investigation; its public upstream
frame contract was inspected instead. Optional TOC dependencies ensure installed
providers initialize first. No private Plater dispatcher hooks/profile changes.

[PlateTweaks](https://www.curseforge.com/wow/addons/platetweaks) provides comparable
secure coloring and could be used directly. Its published page documents rules,
but no settings-registration API for a thin PWT adapter; its All Rights Reserved
implementation/assets were not copied. The PWT remainder uses Blizzard's native
facilities directly. The [ElvUI filtering guide](https://github.com/tukui-org/ElvUI/wiki/filters-retail)
is useful for existing aura displays; its whitelist restrictions differ from the
current AuraSlot candidate-filter implementation, so it is not the sole API authority.

Primary source inspected: Gethe's Blizzard UI source mirror, live snapshot on
2026-11-06 (repository head observed `297d7aaaa736f346b3e036f38ee088eaf7f8c07f` is not used as a version gate; capability
detection is used). Relevant files:
[slot assignment](https://github.com/Gethe/wow-ui-source/blob/live/Interface/AddOns/Blizzard_AuraContainer/Blizzard_AuraContainerSlots.lua),
[custom container](https://github.com/Gethe/wow-ui-source/blob/live/Interface/AddOns/Blizzard_AuraContainer/Blizzard_CustomAuraContainer.lua),
[button rendering](https://github.com/Gethe/wow-ui-source/blob/live/Interface/AddOns/Blizzard_AuraContainer/Blizzard_CustomAuraButton.lua),
[identity/access restrictions](https://github.com/Gethe/wow-ui-source/blob/live/Interface/AddOns/Blizzard_AuraContainer/Blizzard_AuraContainerUtil.lua),
[Plater attachment contract](https://github.com/Tercioo/Plater-Nameplates/blob/master/Plater.lua).
The requested Warcraft Wiki API-notes page returned HTTP 403; source inspection
replaced it. No third-party code or network downloads are needed by the add-on.

## Validation and first client acceptance

`tests/run.py` runs the model, compositor and lifecycle fixtures. Optional
`--aura-source /path/to/Blizzard_AuraContainer` executes unmodified Blizzard Lua
contracts for slot options, native show/clear and identity filtering. Neither suite
emulates engine access restrictions, secret values, GPU compositing or combat taint.

After a separately authorized trial deployment, `/reload` loads this existing add-on:

1. Guardian: open settings; check cyan Incarnation above orange Dream Conduit.
   Trigger each and both, in and out of combat. Verify native progress, immediate
   fallback and hiding when neither is active. If Incarnation never appears,
   report that separately from priority; substitute two known accessible buffs
   temporarily (e.g. Mark of the Wild `1126` and Barkskin `22812`) to isolate mechanism.
2. Balance: apply Moonfire only, Sunfire only, both; remove/expire each. Verify pink,
   cyan, combined color, then no border. Verify another Druid's DoTs do not count.
   Test repeated plate recycling and pulls with newly appearing enemies in combat.
3. Add a third debuff and test all seven nonempty subsets before considering the
   three-effect mode validated. Compare frame rate/CPU in an ordinary multi-target
   pull with feature enabled and disabled; no FPS claim is established locally.
4. Confirm threat remains readable, target/cast/absorb indicators and clicking work,
   and Plater settings are unchanged. Try without optional providers where practical.
5. Switch all Druid specs, then a non-Druid; verify matching presets/no foreign bars.
   Reload/change character; verify lists, priorities, inheritance, hex colors and
   S/V persist. Reset an override and confirm inheritance returns.
6. Edit/apply/disable during combat; confirm the old display remains until combat
   ends and queued changes apply once. Check Lua errors and taint/protected actions.
7. Verify existing Objective Tracker, OPie and tooltip behavior remains unchanged.

Stop expansion if steps 1–2 fail. Remaining gaps are spellbook-to-aura discovery,
verified Ascendant states, health tinting and live acceptance;
they are not silently replaced by out-of-combat tracking.

Existing explicit bar-list overrides are preserved. To adopt the revised Guardian
preset after customizing its list, select Guardian overrides and Reset to inherited.
This also resets other Guardian overrides; saved global and Druid settings remain.

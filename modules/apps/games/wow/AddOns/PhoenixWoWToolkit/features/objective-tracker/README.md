# Objective Tracker

## Intentions and options

Preserve category headings, controls and layout while reducing tracker chrome. Both
account-wide options default on and have independent behavior:

- Hide the global All Objectives text/background and minimize button. The global
  button is hidden, so it has no invisible click target.
- Make section minimize buttons transparent with `SetAlpha(0)`, preserving their
  original click regions and collapse/expand handlers.

Disabling restores the recorded visibility/alpha, including later requests from
Blizzard or a skin. Keep spacing unchanged: reclaiming the global gap would require
writing Blizzard layout state. This feature never forces the tracker expanded.

## Integration and constraints

Discover modules through `ObjectiveTrackerFrame:ForEachModule()` with `modules` /
`MODULES` fallback. Traverse nested containers, exclude the root header and skip
custom modules without `Header.MinimizeButton`. Post-hook container updates/additions
and visual setters; no polling, mouse/binding changes or method replacement.
Blizzard caches Update during OnLoad, so retain the global Header:Show observer and
the captured-function regression case. Hooks remain gated when disabled.

The installed ElvUI skin uses these same headers and changes textures; alpha avoids
rewriting that skin. Replacement trackers outside Blizzard's container are not
adopted. Writes to protected controls or controls with protected ancestors are deferred
until combat ends; a newly protected control can remain visible until then.

Sources: Blizzard [container](https://github.com/Gethe/wow-ui-source/blob/live/Interface/AddOns/Blizzard_ObjectiveTracker/Blizzard_ObjectiveTrackerContainer.lua)
and [module](https://github.com/Gethe/wow-ui-source/blob/live/Interface/AddOns/Blizzard_ObjectiveTracker/Blizzard_ObjectiveTrackerModule.lua).

## Validation

From the add-on root: `lua features/objective-tracker/tests/test.lua .`.
The fixture covers delayed initialization, independent toggles, clickable transparent
buttons, absent/replaced controls, skin restoration, cached updates, combat deferral
and preference reuse. It does not emulate real rendering or taint.

Player acceptance: both options worked in the existing ElvUI/ToxiUI setup before this
architecture move. Recheck after deployment: reload, quest updates, zone changes,
Campaign/Quests/World Quests headers, both invisible section clicks, absence of a
global-button hotspot, disable/restore and combat transitions. Inspect BugSack.

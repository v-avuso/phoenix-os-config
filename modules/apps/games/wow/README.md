# World of Warcraft Retail

## Intentions

Keep the existing Lutris installation and ToxiUI foundation. Install compatible packages additively;
never overwrite private settings, launch WoW or reload its UI. [Technical notes](docs.md) own sources,
feature ownership and recovery; [VISION.md](VISION.md) describes future possibilities.

**Installed:** 44 managed packages, including Simple Addon Manager and Chatty Little NPC with Vanilla
and Midnight English voices. Existing ElvUI/ToxiUI settings remain unchanged. No UI settings or bindings
have been applied automatically. Missing provider credentials still block several requested packages.

## Manual configuration — first play

Open WoW yourself **after package writes finish**. These are one-time native changes, not a preset
that will overwrite later customization. No ToxiUI installer reset is needed.

- [ ] **Keep a rollback:** `/ec` → **Profiles → Export Profile**, save privately. The private WTF backup
  described in [recovery](docs.md#settings-portability-and-recovery) also preserves bindings; profile
  exports alone do not. Dismiss optional ElvUI/ToxiUI installer resets.
- [ ] **Read quests deliberately:** right-click the WoW-Pro minimap button → **Main → Automation**;
  disable **Auto Select**, **Auto Accept**, **Auto Turnin** to keep Dialogue UI in control of interaction.
- [ ] **Navigation:** **Esc → Settings → AddOns → Waypoint UI → Extensions → TomTom**: keep tracking
  enabled. Disable **Auto-Replace Waypoint** if manually selected destinations should survive new
  waypoints. Otherwise retain its guide-led default. Verify one guide destination before playing.
- [ ] **Hold casting:** **Esc → Settings → Gameplay → Combat → Press and Hold Casting** → enabled
  (also mirrored under Accessibility). Alternatively `/console ActionButtonUseKeyHeldSpell 1`.
  Leave key-down and empowered-spell settings unchanged; they control different behavior.

### Native action-bar preset (out of combat)

This uses the existing profile and slots. Do not rerun the ToxiUI installer. The
[ElvUI native implementation](https://github.com/tukui-org/ElvUI/tree/main/ElvUI/Game/Shared/Modules/ActionBars)
owns paging, binding and special-state handling; in-game acceptance is still required.

1. `/ec` → **ActionBars → Player Bars → Bar 1**: enabled, **Mouseover** off,
   **Inherit Global Fade** off, **Alpha** 1. Keep its existing visibility conditions.
   `/moveui`: place Bar 1 bottom-center and minimap bottom-right if needed. For ordinary utility bars,
   keep enabled, **Mouseover** on, **Inherit Global Fade** off, **Alpha** 1. Keep essential cooldowns
   visible until you have another reliable display. Leave pet, stance, extra and zone bars intact.
2. Bar 1 → **Action Paging**: privately copy the current class string. **Prepend** this exact text,
   preserving every original clause after it, and add no final unconditional page number:

   ```text
   [nomod:alt,mod:shift] 2; [nomod:alt,mod:ctrl] 3;
   ```

   Shift selects page 2, Ctrl page 3; release restores the original base/form page. Alt suppresses
   these modifier pages. Native vehicle/override/possess handling still takes priority. Manually
   selected pages 2–6 also have native priority: return to page 1 before testing. Pages 2/3 share
   existing slots; **populate them yourself**. Existing custom modifier clauses require inspection.
3. `/kb`: check base keys `1`–`0` select main-bar slots 1–10. The commands below deliberately replace
   conflicting numeric modifier bindings. First move pet shortcuts to **Ctrl+Shift+1–0**, preserving
   accessible pet controls; inspect these chords in Key Bindings first if you already use them:

   ```lua
   /run if InCombatLockdown() then return end for i=1,10 do SetBinding("CTRL-SHIFT-"..(i%10),"BONUSACTIONBUTTON"..i) end SaveBindings(GetCurrentBindingSet())
   ```

   Then route Shift/Ctrl numeric keys through the visible main-bar buttons:

   ```lua
   /run if InCombatLockdown() then return end for i=1,10 do for _,m in ipairs({"SHIFT-","CTRL-"}) do SetBinding(m..(i%10),"ACTIONBUTTON"..i) end end SaveBindings(GetCurrentBindingSet())
   ```

   Both commands fit the native chat-command limit. They save the current account/character binding
   set, preserve base/Alt/movement keys and do not fill action slots. **Ctrl+Shift** intentionally
   activates pet abilities, although Shift's page may be displayed. Minus/equals bindings are unchanged.
4. Verify hold/release and casts, normal page, Shift/Ctrl pages, Alt, each Druid form/stealth, pet
   shortcuts, vehicles and special buttons when available. Use `/reload` yourself only if requested by
   the UI, after updates finish. These behaviors have **not** been tested in game.

## Optional refinements — play first

- **Addon management:** **Esc → AddOns** uses Simple Addon Manager. Avoid mass disabling packages or
  loading arbitrary profiles; retain required dependencies. WindTools already owns moving Blizzard
  windows; BlizzMove was omitted to avoid a second mover.
- **Layout:** `/tx settings`, `/ec`, `/moveui`; **UnitFrames → Group Units → Party/Raid** for group sizes.
  Keep native 4K scaling initially. Do not import a competing complete UI preset.
- **Gathering:** GatherMate2 settings → **Import** → installed GatherMate2_Data; `/routes` plans routes.
- **Navigation:** Waypoint UI → **Appearance → Navigator → Show Arrow** off avoids a duplicate arrow
  while retaining TomTom's functional arrow. Hiding TomTom can clear the adopted destination. Avoid
  `/wp` (two addons register it); use `/wow-pro` and `/waypoint`.
- **Camera:** F1 during Dialogue UI interaction → **Camera → Camera Movement → Off** if unwanted.
- **Voices:** `/clnsettings` → **Installed Voiceover Packs**; test a Tirisfal NPC and volume. Auto-play
  defaults on, queued speech continues after dialogue closes. Missing recordings can mean incomplete coverage.
- **Combat:** `/dbm`, `/gtfo test`, `/mdt`; validate actual encounters. Details remains unavailable.

## Package maintenance

```sh
wow-addons search quest
wow-addons list --format detailed
wow-addons install SOURCE
wow-addons remove SOURCE
wow-addons sync
wow-addons update
systemctl --user list-timers wow-addons-update.timer
journalctl --user -u wow-addons-update.service -u wow-addons-update-notify.service
```

Close WoW before interactive package changes. `wow-addons` selects `phoenix-retail` and serializes
operations. Edit [wow-addons.json](wow-addons.json) and deploy before `sync` uses a changed desired set.
Removing a manifest entry never automatically deletes installed packages.

The timer runs at **05:00 Europe/Berlin**, with persistent catch-up when the user manager returns.
It skips successfully if WoW is detected before sync/update or a retry; a skip waits until the next
scheduled run (or a manual run after closing WoW). Failures retry after **1, 5 and 15 minutes** following
previous failures, then stop and send one local desktop notification. Success and skips are silent.
Logs remain in the journal; there are no configuration imports or success notifications.

Do not launch WoW while a package update is already writing files: preflight detection cannot lock
an independent Lutris launcher. Loaded Lua is not hot-patched; new addons can require reopening WoW.
Large voice-package checks can take minutes and several GB RAM. See [source access](docs.md#provider-access-and-recovery-options)
for missing packages; no new credentials are needed for the working installed collection.

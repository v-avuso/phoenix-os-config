# World of Warcraft Retail

## Intentions

Keep the existing Lutris installation and ToxiUI setup; add maintained Midnight add-ons for stories,
exploration, collecting and group play. Package updates never apply settings, write WTF, launch the game
or reload its UI.

**Applied configuration:** upstream add-on defaults only. Existing ElvUI/ToxiUI profiles remain
untouched. The main collection and Chatty Little NPC base are installed with Vanilla and Midnight
English voice packs (43 managed packages). Native update and manifest/database checks passed.
In-game acceptance is separate; see the [package status and technical notes](docs.md).

## Manual configuration — first play

Allow a few minutes after opening WoW yourself. Wait for any add-on update to finish before a manual
reload; newly installed add-ons may require reopening the game.

- [ ] **Keep the existing interface:** dismiss any optional ElvUI/ToxiUI installer reset. Applying a
  ToxiUI installer profile overwrites the current profile.
- [ ] **Place the minimap if needed:** `/moveui` → drag the minimap mover to the bottom-right → finish
  moving. Keep the rest of the existing layout.
- [ ] **Read quests deliberately:** right-click the **WoW-Pro minimap button** (or **Esc → Settings →
  AddOns → WoW-Pro**). Under **Main → Automation**, turn **Auto Select**, **Auto Accept**, and **Auto
  Turnin** off. These default to on and overlap story interaction through Dialogue UI.
- [ ] **Check navigation:** **Esc → Settings → AddOns → Waypoint UI → Extensions → TomTom**: leave
  **Track TomTom Waypoints** on (default). Turn **Auto-Replace Waypoint** off if you want to preserve a
  manually selected destination; leave it on for guide-led navigation. Right-click a TomTom world-map
  waypoint → **Set as waypoint arrow** and check the Waypoint UI destination. If two arrows are
  distracting, use the optional display setting below.
- [ ] **Check usability:** talk to an NPC, follow a guide waypoint, read text at normal viewing
  distance, and confirm current unit/group frames are readable. No automatic layout, scaling or
  keybinding changes have been applied.

## Optional refinements

- **Layout:** `/tx settings` opens ToxiUI; `/ec` opens ElvUI; `/moveui` moves frames, including the
  minimap. `/ec` → **UnitFrames → Group Units → Party/Raid** adjusts group-frame sizes. Keep stock 4K
  scaling initially; choose changes by readability. ToxiUI offers horizontal/vertical layouts, without a
  verified named healer preset.
- **Action bars:** after exporting the current profile, `/ec` → **ActionBars → Player Bars → Bar 1**:
  **Mouseover** off, **Inherit Global Fade** off, **Alpha** 1. For utility bars, enable **Mouseover**,
  disable **Inherit Global Fade**, and keep the bars enabled/populated. Hide only genuine utility
  bars; keep any bar showing essential combat cooldowns visible until native cooldown views are verified. `/moveui` places them at the
  bottom. Preserve special bars, existing actions and bindings. Nothing is applied automatically.
- **Shift/Ctrl paging (optional, out of combat):** export the current profile, then `/ec` →
  **ActionBars → Player Bars → Bar 1 → Action Paging**. Privately copy the actual class-specific
  string; preserve every existing native clause in its original order. Only if there is **no custom
  unconditional catch-all**, append `[nomod:alt,mod:shift] 2; [nomod:alt,mod:ctrl] 3;` with no final
  unconditional page number. Stop if unsure about the current string. Shift selects page 2, Ctrl page 3;
  Alt suppresses both, and Shift wins together. Keep pages 7–10 reserved for forms. Retained Druid
  clauses take priority, so this example affects only the base/humanoid bar. Pages 2/3 use existing
  shared slots; populate deliberately. Inspect `/kb` and game Key Bindings first: ten Shift+number
  CLICK bindings were observed, while effective Ctrl bindings remain unknown. Do not clear bindings;
  paging does not remap modified keys, so same-slot casts may conflict. Check hold/release, casts,
  cooldowns, forms and vehicle/special bars before relying on it. See [technical limits](docs.md#optional-native-action-bars).
- **Dialogue camera:** press **F1 during NPC interaction** → **Camera → Camera Movement**; choose
  **Off** only if you dislike motion. Dialogue UI owns NPC camera; optional DynamicCam owns general
  world camera and is not currently configured.
- **Gathering data:** open GatherMate2 in WoW's add-on settings → **Import** and choose the installed
  GatherMate2_Data dataset. Installing the dataset alone does not populate nodes. `/routes` opens route
  planning after selecting desired nodes.
- **One navigation arrow:** keep TomTom's arrow and Waypoint UI tracking active; Waypoint UI →
  **Appearance → Navigator → Show Arrow** off hides only its arrow. Confirm the destination/guide still
  advances. TomTom cannot make its arrow fully transparent through supported settings. Avoid `/wp`: both
  add-ons register it.
- **Tirisfal guide:** use WoW-Pro's guide picker and select the guide matching your current progress.
  `/wow-pro load-guide JiyDk0105` loads **Forsaken: Intro** only when starting that introduction; it
  need not match an existing Tirisfal quest log.
- **Collections:** `/btwquests` opens quest chains; `/rarity` opens drop tracking. Keep add-on defaults
  first and reduce overlapping tooltips/pins only as needed.
- **Combat:** `/dbm` opens DBM's test/anchor controls; `/gtfo options` and `/gtfo test` check audible
  warnings; `/mdt` opens dungeon planning. Test in actual content; Midnight limits GTFO's detectable
  hazards. Keep one visible damage-meter owner.
- **Bindings:** if available, `/opie` and `/opie rings` configure rings. Choose unused keys in game for
  rings, LiteMount and fishing; no binding preset is applied.
- **Voice:** `/clnsettings` → **Playback**: **Auto-Play Voiceovers** is already on; **Quest Playback
  Mode** and **Gossip Playback Mode** default to queues that continue after closing dialogue. Keep these
  defaults first; optionally choose **Stop when dialog closes**. Check **Installed Voiceover Packs**,
  talk to a Tirisfal NPC, and check volume (default audio channel **Master**). Missing recordings mean
  coverage is incomplete; installing a pack does not prove every quest is voiced.

## Package maintenance

```sh
wow-addons list --format detailed
wow-addons update
systemctl --user list-timers wow-addons-update.timer
journalctl --user -u wow-addons-update.service
```

The timer updates managed packages daily at **09:00 Europe/Berlin** and catches a missed run when the
user manager returns. It never imports profiles. The desired set lives in
[`wow-addons.json`](wow-addons.json); changes require deployment before `wow-addons sync` uses the new
manifest. Removing an entry does not uninstall it. See [technical notes](docs.md) for source decisions,
blocked packages, installation paths, authentication, backup and portable settings.

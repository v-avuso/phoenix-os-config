# World of Warcraft Retail — first play

## Current setup

**69 desired instawow packages + 16 WowUp-CF packages.** The original ElvUI/ToxiUI profile,
bindings, casting settings and private WTF files are preserved. The user has completed ToxiUI's in-game installer and customization;
this addon batch preserves those current settings and does not launch WoW.
**No addon-specific configuration overrides, new ToxiUI profiles or action-bar bindings have been
programmatically applied.** The checklist below is manual guidance, not an installed preset.

BtWQuests now includes every resolved maintained Retail expansion from Burning Crusade through
Midnight, plus BFA, Shadowlands, Dragonflight and TWW prologues. `/btwquests` opens its expansion picker;
modules load on demand. The separate Midnight prologue has no usable official GitHub release asset.
No deprecated Classic-client package or duplicate Midnight package was added.

WowUp owns Details!, RareScanner, World Quest Tracker, TSM, Leatrix Plus/Maps, OPie, DynamicCam,
Ultimate Mouse Cursor, Better Fishing, Home Bound, BugGrabber/BugSack, Syndicator and GuildFinder+.
The original **46 instawow package records** are protected by Ignore / Auto Update off in WowUp.
The **12 newer BtWQuests package records** may need discovery and Ignore reconciliation; the
**16 CurseForge installations remain WowUp-managed**, with auto-update off. Package records are not
individual folders: after cleanup, 84 packages supply 151 AddOns folders, including bundled modules. Do not
reinstall or adopt either manager's packages in the other. The ten new English voice packs below
are also instawow-owned and must be ignored if WowUp discovers them.

## Crafting and TSM companion

**WorthIt — exact match, installation blocked (2026-10-29):** InstaWow's current
catalogue lists `curse:worthit`, matching [WorthIt by DalaGG](https://www.curseforge.com/wow/addons/worthit)
(project 348878). The native install dry-run fails with `package source is disabled:
access token missing`. No exact alternative source was found in the bounded search.
This attempt **did not install WorthIt**; its installation status in WowUp was not
checked and may change independently. It is absent from the InstaWow daily update
manifest; adding the blocked source would make scheduled sync fail. Before any later
InstaWow installation, check existing folders and WowUp ownership to avoid two
managers updating the same add-on. Inclusion in the 05:00 Berlin InstaWow updates
requires a supported, accessible source. The separate Guides,
Gold Tracker and Leveling packages are not substitutes.

CraftSim **27.0.7** is installed as `github:derfloh205/CraftSim`, including the existing
05:00 Berlin instawow update flow. It uses the built-in Blizzard professions UI and can
use TSM prices; no crafting settings or WTF files were changed. If WowUp discovers
**CraftSim**, set **Ignore / Auto Update off** before allowing it to update packages.

**TSM Desktop App** opens the pinned community Linux companion in the foreground.
Desktop notifications are disabled through its native `notifications_enabled` setting;
Home Manager reasserts this preference while preserving other TSM settings. A running
instance picks up the change on its next launch.
Before first companion sync, set **TradeSkillMaster** and **TSM_AppHelper** to
**Ignore / Auto Update off** in WowUp. The companion updates these addons itself and
writes price data; it must be their only updater. Sign in through the app (never send
credentials to an agent), select the WoW base directory:

```text
/home/v/Games/battlenet/drive_c/Program Files (x86)/World of Warcraft
```

Select your realms and install **TSM_AppHelper** from the companion's **Addon Versions**
tab, or use your addon manager and then ignore it. instawow's exact CurseForge source
requires an unavailable access token; the catalogue search found no exact alternative.
AppHelper is therefore **not installed by this task** and is absent from the manifest.

The existing **Battle.net** launcher also starts `wow-tsm-session.service`. After the
initial login/setup, its TSM instance starts in the tray and continues after Battle.net
closes. A small watcher checks every two seconds and sends TSM a graceful termination
signal after all current-user WoW clients close. It permits two minutes for Battle.net
to appear, waits while Battle.net is open, and permits one minute for the game handoff
after Battle.net exits. Cancelling a launch therefore cleans up TSM too. Other games
launched from Battle.net do not extend the session. Starting Lutris through another
entry point does not start the watcher.

A manually started TSM instance is never stopped by the watcher. Both routes share a
runtime lock; if already running, the standalone launcher asks you to use the tray
icon to inspect it. First-time authentication can still display a login dialog during
automatic startup. The standalone launch overrides the saved tray-start preference
for that invocation only. Manage the automatic session with:

```sh
systemctl --user status wow-tsm-session.service
systemctl --user stop wow-tsm-session.service
journalctl --user -u wow-tsm-session.service
```

Verify on your next play session: TSM remains running after Battle.net exits, receives
price data after account setup, and closes shortly after WoW exits. A manual TSM launch
must remain running when WoW closes. The app is community maintained, not officially
supported by TradeSkillMaster on Linux. Technical packaging rationale is in [docs.md](docs.md#tsm-and-configuration-ownership).

## Small utility batch — 2026-10-27

**Hide Vendor Sell Price rejected:** the player confirmed it does not remove the vendor price
in this ElvUI/ToxiUI setup. `github:delulunia/HideVendorSellPrice` has been removed from the desired
manifest. Remove its installed record and `Interface/AddOns/HideVendorSellPrice` only with
WoW closed, using the workflow below. No replacement addon or tooltip/profile changes are requested.

### Post-game removal

Close WoW and WowUp first, and keep them closed throughout. In a terminal, run each step only after
the preceding step succeeds. Stop the timer to prevent an automatic race; let any already-running
updater finish by waiting for the existing shared lock. Do not run sync against the old deployed
old manifest containing that addon: it would reinstall the removed addon.

```sh
cd /home/v/repos/code/phoenix-os-config
systemctl --user stop wow-addons-update.timer
flock -w 3600 "$HOME/.local/state/phoenix-wow/lock" true
phoenix-switch --worktree /home/v/repos/code/phoenix-os-config
systemctl --user stop wow-addons-update.timer
jq -e 'length == 69 and index("github:delulunia/HideVendorSellPrice") == null' \
  /etc/phoenix-agent/activated-source/modules/apps/games/wow/wow-addons.json
wow-addons remove github:delulunia/HideVendorSellPrice
wow-addons sync
wow-addons list --format json github:delulunia/HideVendorSellPrice | jq -e 'length == 0'
test ! -e '/home/v/Games/battlenet/drive_c/Program Files (x86)/World of Warcraft/_retail_/Interface/AddOns/HideVendorSellPrice'
systemctl --user start wow-addons-update.timer
systemctl --user list-timers wow-addons-update.timer
```

`phoenix-switch` above is the human terminal route; an agent resuming this cleanup must use the
repository's `ai-broker --task wow-addon-removal --reason 'Deploy the requested addon removal' --
phoenix-switch --worktree /home/v/repos/code/phoenix-os-config` route instead.
If deployment or verification fails, stop before removal/sync and leave the timer stopped until
resolved. Check the source comparison before deploying if other repository changes have accumulated.
The managed `wow-addons remove` uses the shared lock and removes only this instawow package's
record/files. Do not delete its directory manually or edit WTF. After successful cleanup, additive
sync will neither restore it nor remove unrelated packages; updates follow the remaining database.

**Manual WowUp-CF fallback — not installed by this batch:** instawow's CurseForge resolver requires
an unavailable access token. No suitable public GitHub/WoWInterface release was found in the bounded
search. Native desktop GUI control is unavailable in this session. Use the existing WowUp-CF client;
do not add these to instawow's manifest or supply a paid provider token.

| Exact package / author | Actual public provider and source URI | Installed folder |
|---|---|---|
| ObjectiveBarManager / M05final | CurseForge: [curse:1109979](https://www.curseforge.com/wow/addons/objectivebarmanager) | **Not installed**; verify WowUp's installed-folder details after installation |
| DamageMeterKeybind / CanadianFteev | CurseForge: [curse:1492150](https://www.curseforge.com/wow/addons/damagemeterkeybind) | **Not installed**; verify WowUp's installed-folder details after installation |

1. With WoW closed, open WowUp-CF → **Get Addons** for the existing Retail client. Search the exact
   names above (or use the linked project URL), verify author/provider and choose a Retail release.
   Publisher pages list 12.1.0 support; exact current archive TOCs/dependencies are **not yet audited**.
   Review any dependency prompt; cancel replacement of an existing instawow-owned addon.
2. Install only those two packages, keep their **Auto Update off**, and retain WowUp ownership.
   Recheck that existing instawow records remain **Ignore / Auto Update off**; do not use Update All.
3. ObjectiveBarManager includes appearance and automatic visibility features, beyond a simple keybind.
   Before relying on it, inspect its settings via the minimap button's right-click. Leave ToxiUI/WindTools
   as the styling owner; disable any OBM appearance overrides and unwanted auto-hide/instance behavior
   through its own UI. Defaults/source compatibility with the current skin remain **unverified**.
   Test `/obm` twice out of combat: tracker must return with the same font, position and styling.
   If styling changes, disable OBM and retain the current tracker. Only after this passes, assign
   **Shift+L** manually in Settings → Keybindings to its tracker toggle; inspect any binding conflict.
4. Settings → Keybindings → **Damage Meter Keybind** → toggle show/hide all windows: choose a key
   manually. Test twice with Blizzard's native meter and confirm the ToxiUI skin stays intact.
   Avoid the separate reset-all-combat-sessions binding. This addon targets the native meter, not Details!.
   Source-level skin compatibility remains unverified until its archive is available for inspection.
5. Check `/bugsack`. Disable only the failing new addon if needed; do not reset ToxiUI or import profiles.
   No keybinding or existing profile was changed by this batch.

## New BtWQuests packages — WowUp Ignore checklist

These are **only the twelve additions from `b7f39af`**. The first eleven publisher labels match the
CurseForge catalogue; no new WowUp row has been observed yet. Match source/name when possible, not
row count alone. The final GitHub package's actual WowUp label is unconfirmed.

| Exact instawow package name | instawow source URI | WowUp lookup label |
|---|---|---|
| BtWQuests: Battle for Azeroth | `wowi:25792` | Same catalogue label |
| BtWQuests: Battle for Azeroth Prologue | `wowi:24769` | Same catalogue label |
| BtWQuests: Cataclysm | `wowi:25552` | Same catalogue label |
| BtWQuests: Dragonflight Prologue | `wowi:26458` | Same catalogue label |
| BtWQuests: Legion | `wowi:24770` | Same catalogue label |
| BtWQuests: Mists of Pandaria | `wowi:25547` | Same catalogue label |
| BtWQuests: Shadowlands | `wowi:25655` | Same catalogue label |
| BtWQuests: Shadowlands Prologue | `wowi:25660` | Same catalogue label |
| BtWQuests: The Burning Crusade | `wowi:25631` | Same catalogue label |
| BtWQuests: Warlords of Draenor | `wowi:25553` | Same catalogue label |
| BtWQuests: Wrath of the Lich King | `wowi:25784` | Same catalogue label |
| BtWQuestsTheWarWithinPrologue | `github:Breeni/BtWQuestsTheWarWithinPrologue` | Unconfirmed; TOC title: BtWQuests: The War Within Prologue |

**Previously installed, not part of these twelve:** BtWQuests core (`wowi:24680`) already bundles
`BtWQuestsMidnight`; Dragonflight (`github:Breeni/BtWQuestsDragonflight`) and TWW
(`github:Breeni/BtWQuestsTheWarWithin`) were already present. Those three package records supply
four BtWQuests folders. Keep them ignored too; do not add a second Midnight package.

## Complete English expansion voice packs

Vanilla and Midnight were retained; the ten additional official packs are now installed. Cataclysm
was installed first for current Tirisfal questing. No playback settings, profiles, action bars or WTF
files were changed. `/clnsettings` → **Installed Voiceover Packs** should show all twelve expansion
packs after your next game start; verify a current quest and your existing audio volume in game.
If a pack is missing from that list, check it is enabled in the character-select **AddOns** menu.
No ToxiUI/profile import or installer reset is needed.
Recordings still depend on upstream quest/gossip coverage, not merely pack installation.

**WowUp Ignore:** after a scan, ignore the ten new package records below and keep Auto Update off.
Match their folder names if WowUp's provider labels differ. Chatty core, Vanilla and Midnight remain
ignored too. Do not adopt these packs into WowUp or reinstall them from CurseForge. Exact source
URIs/releases are in [technical notes](docs.md#english-voice-pack-coverage).

| Expansion | New folder — instawow-owned; ignore in WowUp |
|---|---|
| Cataclysm | `ChattyLittleNpc_Cataclysm_voiceovers` |
| Battle for Azeroth | `ChattyLittleNpc_Battle_for_Azeroth_voiceovers` |
| Dragonflight | `ChattyLittleNpc_Dragonflight_voiceovers` |
| Legion | `ChattyLittleNpc_Legion_voiceovers` |
| Mists of Pandaria | `ChattyLittleNpc_Mists_of_Pandaria_voiceovers` |
| Shadowlands | `ChattyLittleNpc_Shadowlands_voiceovers` |
| The Burning Crusade | `ChattyLittleNpc_The_Burning_Crusade_voiceovers` |
| The War Within | `ChattyLittleNpc_The_War_Within_voiceovers` |
| Warlords of Draenor | `ChattyLittleNpc_Warlords_of_Draenor_voiceovers` |
| Wrath of the Lich King | `ChattyLittleNpc_Wrath_of_the_Lich_King_voiceovers` |

All ten were managed through instawow; no WowUp-only fallback is required.

## Manual configuration — first in-game test

- [ ] Finish package writes, close WowUp, then launch WoW yourself. Retain the existing ToxiUI profile;
  dismiss optional full installer resets. No action-paging or keybinding changes are required.
- [ ] Keep existing Press and Hold Casting. If checking it: **Esc → Settings → Gameplay → Combat**.
- [ ] BlizzMove owns moving Blizzard windows; WindTools natively defers when it loads. If both appear
  active: `/ec` → **WindTools → Misc → Move Frames → Enable** off and accept its reload prompt.
- [ ] Keep Leatrix Plus repairs/junk selling and quest automation off; ElvUI owns repair/sell behavior.
  Enable other QoL options selectively. Retain one main objective tracker after inspecting WQT.
- [ ] For a conservative camera baseline, during Dialogue UI interaction use **F1 → Camera → Camera
  Movement → Off**; DynamicCam remains the general-world camera owner. Refine later.
- [ ] `/opie` configures rings; keep OPie's built-in skin. **OPie: ElvUI Skin 1.5.1 is incompatible with
  installed OPie's Midnight API** and was not installed. No new bindings were assigned.
- [ ] `/syns item-name` searches Syndicator's recorded inventory; visit each character/bank/mail to
  populate it. ElvUI still owns bags; Altoholic is omitted. TSM currently has no refreshed companion
  price data; do not set up an unsupported Linux companion today.

Optional: `/dbm` tests warning anchors; `/bugsack` reviews captured errors; `/clnsettings` checks voice
packs. WoW-Pro minimap settings → **Main → Automation** off for deliberate quest reading. UI, combat,
quest navigation, voices and addon interactions still need this real game session.

## Slash commands

Verified against the installed addons' command registrations/handlers; this is not an in-game test.
One useful command per addon or purpose is listed; aliases/debug commands are omitted. Avoid `/wp`:
WoW-Pro and Waypoint UI both register it.

| Command | Addon / purpose |
|---|---|
| `/btwquests` | **BtWQuests** — quest chains and expansion picker. |
| `/bugsack` | **BugSack** — captured Lua errors. |
| `/clnsettings` | **Chatty Little NPC** — voice playback settings. |
| `/dbm` | **Deadly Boss Mods** — encounter-warning controls. |
| `/dc` | **DynamicCam** — camera settings. |
| `/details` | **Details!** — damage-meter commands. |
| `/ec` | **ElvUI** — configuration. |
| `/gtfo` | **GTFO** — alert commands and help. |
| `/handynotes` | **HandyNotes** — map-pin settings. |
| `/kb` | **ElvUI** — keybinding mode; changes remain manual. |
| `/keystoneloot` | **KeystoneLoot** — dungeon/raid loot planning. |
| `/ltm` | **Leatrix Maps** — map settings. |
| `/ltp` | **Leatrix Plus** — individual QoL options. |
| `/mdt` | **Mythic Dungeon Tools** — dungeon routes. |
| `/moveui` | **ElvUI** — frame movers. |
| `/opie` | **OPie** — ring settings. |
| `/rarity` | **Rarity** — drop tracking and options. |
| `/routes` | **Routes** — gathering-route configuration. |
| `/sam` | **Simple Addon Manager** — addon-management commands. |
| `/syns item-name` | **Syndicator** — search recorded inventory. |
| `/tomtom` | **TomTom** — navigation settings. |
| `/tsm` | **TradeSkillMaster** — economy interface and commands. |
| `/tx settings` | **ToxiUI** — settings. |
| `/warpdeplete` | **WarpDeplete** — Mythic+ timer options. |
| `/wow-pro` | **WoW-Pro** — guide commands. |

## WowUp window closing — manual preference

**Options → Application → Minimize on Close → Off.** This is WowUp's persistent application setting.
Then close the window and confirm the tray icon disappears. Until changed, use the tray icon's
**Quit** action when you want to terminate WowUp. The setting is currently on and **was not changed**
here: native GUI control is unavailable, and no supported external settings command was verified.
No private application-state file was patched. See the [official application options](https://wowup.io/guide/options/application).

## Maintenance

```sh
wow-addons list --format detailed
wow-addons sync
wow-addons update
systemctl --user list-timers wow-addons-update.timer
journalctl --user -u wow-addons-update.service
```

Instawow owns [wow-addons.json](wow-addons.json); deploy edits before `sync` uses the changed manifest.
Its **05:00 Europe/Berlin** persistent timer, 1/5/15-minute retries, terminal-only notification and
WoW-running skips are unchanged. Close WoW before interactive writes; do not launch during updates.

**Next WowUp scan:** reconcile the twelve BtWQuests records and ten voice-pack records listed above.
For BtWQuests, when discovered,
filter **My Addons → BtWQuests**, select those rows and set **Ignore** fully checked / **Auto Update**
off. A mixed selection may need a second Ignore toggle. Do not select the entire mixed-manager
collection and ignore it wholesale. Verify the original 46 packages remain ignored after a full rescan,
including bundled Midnight; keep the 15 CurseForge installations managed by WowUp.
Update only WowUp's own fifteen packages individually, with WoW closed; avoid unrestricted Update All.

See [inventory, sources and recovery](docs.md) for exact providers, ownership and the private backup.
[VISION.md](VISION.md) describes future direction, not additional first-play requirements.

## Low-priority TODO

- Consider a `phoenix-wow-update` convenience command that triggers the existing updater and opens
  WowUp. **Not implemented**; reuse the existing update service rather than adding another scheduler.

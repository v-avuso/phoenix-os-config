# World of Warcraft Retail — first play

## Current setup

**58 instawow packages + 15 WowUp-CF packages; 140 addon folders.** The original ElvUI/ToxiUI profile,
bindings, casting settings and private WTF files are preserved. WoW has not been launched for testing.
**No addon-specific configuration overrides, new ToxiUI profiles or action-bar bindings have been
programmatically applied.** The checklist below is manual guidance, not an installed preset.

BtWQuests now includes every resolved maintained Retail expansion from Burning Crusade through
Midnight, plus BFA, Shadowlands, Dragonflight and TWW prologues. `/btwquests` opens its expansion picker;
modules load on demand. The separate Midnight prologue has no usable official GitHub release asset.
No deprecated Classic-client package or duplicate Midnight package was added.

WowUp owns Details!, RareScanner, World Quest Tracker, TSM, Leatrix Plus/Maps, OPie, DynamicCam,
Ultimate Mouse Cursor, Better Fishing, Home Bound, BugGrabber/BugSack, Syndicator and GuildFinder+.
The original **46 instawow package records** are protected by Ignore / Auto Update off in WowUp.
The **12 newer BtWQuests package records** still need discovery and Ignore reconciliation; the
**15 CurseForge installations remain WowUp-managed**, with auto-update off. Package records are not
individual folders: the 73 packages supply 140 AddOns folders, including bundled modules. Do not
reinstall or adopt either manager's packages in the other.

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

**Next WowUp scan:** reconcile only the twelve new package records listed above. When discovered,
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

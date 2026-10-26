# World of Warcraft Retail — first play

## Current setup

**58 instawow packages + 15 WowUp-CF packages; 140 addon folders.** The original ElvUI/ToxiUI profile,
bindings, casting settings and private WTF files are preserved. WoW has not been launched for testing.

BtWQuests now includes every resolved maintained Retail expansion from Burning Crusade through
Midnight, plus BFA, Shadowlands, Dragonflight and TWW prologues. `/btwquests` opens its expansion picker;
modules load on demand. The separate Midnight prologue has no usable official GitHub release asset.
No deprecated Classic-client package or duplicate Midnight package was added.

WowUp owns Details!, RareScanner, World Quest Tracker, TSM, Leatrix Plus/Maps, OPie, DynamicCam,
Ultimate Mouse Cursor, Better Fishing, Home Bound, BugGrabber/BugSack, Syndicator and GuildFinder+.
The manager audit confirms existing instawow packages are ignored and auto-update is off; the fifteen
CF packages also have auto-update off. Do not reinstall or adopt either manager's packages in the other.

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

**Next WowUp scan:** the twelve new BtWQuests folders are not registered there yet. When discovered,
filter **My Addons → BtWQuests**, select those rows and set **Ignore** fully checked / **Auto Update**
off. A mixed selection may need a second Ignore toggle. Do not select the entire mixed-manager
collection and ignore it wholesale. Keep all instawow modules ignored, including bundled Midnight.
Update only WowUp's own fifteen packages individually, with WoW closed; avoid unrestricted Update All.

See [inventory, sources and recovery](docs.md) for exact providers, ownership and the private backup.
[VISION.md](VISION.md) describes future direction, not additional first-play requirements.

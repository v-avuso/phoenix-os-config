# World of Warcraft Retail — first play

## Intentions and current state

Keep the existing Lutris game, ElvUI/ToxiUI profile, bindings and casting settings. **46 packages are
installed through instawow**, including newly added BlizzMove and KeystoneLoot. WowUp-CF is provided
by Nixpkgs for the remaining CurseForge packages. It has **not been launched or configured** here:
native GUI control is unavailable. Its first-run protection below is required before installing anything.
No action-paging preset or keybinding commands need to be applied today.

## Manual configuration — before first play

### 1. Protect existing packages in WowUp-CF (once, with WoW closed)

1. Launch **WowUp-CF** from the application menu, or run `wowup-cf`. Keep automatic updates off;
   do not use **Update All**, **Re-Install**, provider switching or automatic adoption.
2. **Options → WoW Clients → Add New**: select this existing executable; no game download/copy:

   ```text
   /home/v/Games/battlenet/drive_c/Program Files (x86)/World of Warcraft/_retail_/Wow.exe
   ```

   Select **Retail**. Edit this client's options: default channel **Stable/Release**, automatic
   updates for new addons **off**. Keep launch-with-system off.
3. **My Addons**, Retail selected, search filter empty: click the list, **Ctrl+A**, right-click →
   **Ignore**. Verify the selection's Ignore checkbox is fully checked and **Auto Update** unchecked.
   A mixed selection can need a second Ignore toggle. Ignoring automatically disables auto-update
   in the packaged version. Include detected bundled modules and unknown/unmanaged rows.
4. Only then use **Get Addons** for new packages. Do not unignore the existing instawow packages.
   Installing new instawow packages later or rescanning WowUp requires checking these flags again.
   If a package wants to replace an existing folder, cancel and resolve ownership first.

These controls are verified against [WowUp's guide](https://wowup.io/guide/my-addons/addons) and its
[v2.22.0 source](https://github.com/WowUp/WowUp.CF/blob/v2.22.0/wowup-electron/src/app/pages/my-addons/my-addons.component.ts).
GUI behavior and provider downloads still need your first-run check; no Ignore flags were set for you.

### 2. Install the highest-value missing addons

In **Get Addons**, choose **CurseForge**, search and install the stable **Retail** versions individually:

1. **Details! Damage Meter**, **RareScanner**, **World Quest Tracker**, **TradeSkillMaster**.
2. **Syndicator** (cross-character inventory; use instead of Altoholic, retain ElvUI bags).
3. As time permits: **Leatrix Plus**, **Leatrix Maps**, **OPie**, **DynamicCam**, **Better Fishing**,
   **Ultimate Mouse Cursor**, **Home Bound**, **!BugGrabber**, then **BugSack**, **GuildFinder+**.

Exact publisher pages/IDs and deferred exceptions are in [the inventory](docs.md#package-catalogue).
Allow official required dependencies only; keep Auto Update off for today's manual CF collection too.
Do not reinstall BlizzMove or KeystoneLoot: instawow already owns them. If a provider refuses a package,
leave it missing and play. Do not import an entire UI pack or use another updater for the same folders.

TSM without its desktop companion lacks refreshed auction-price data. Do not install an unofficial
Linux companion or enter TSM credentials today; [ownership limitations](docs.md#tsm-and-configuration-ownership)
are separate from installing the main addon.

### 3. Launch WoW yourself

- [ ] Close WowUp after installations finish; ensure no updater is still writing files. Keep the
  existing ElvUI/ToxiUI profile and dismiss optional installer resets.
- [ ] Keep existing Press and Hold Casting. If desired and currently off: **Esc → Settings → Gameplay
  → Combat → Press and Hold Casting**. No CVars or bindings were changed here.
- [ ] BlizzMove owns Blizzard-window movement; WindTools detects it and disables its own mover.
  If both appear active: `/ec` → **WindTools → Misc → Move Frames → Enable** off, then accept its
  requested `/reload`. Runtime integration still needs this first-login check.
- [ ] If installing DynamicCam, avoid two NPC-camera owners: during Dialogue UI interaction press
  **F1 → Camera → Camera Movement → Off** for the simplest conservative baseline. Refine later.
- [ ] If installing Leatrix Plus, keep its repair/junk-selling and quest automation off; ElvUI owns
  repairs/selling. Do not enable every QoL toggle. Keep one main objective tracker.
- [ ] `/keystoneloot` opens loot planning. With Syndicator, visit each character/bank/mail you want
  indexed; `/syns item-name` searches recorded inventory. No bag replacement is required.

No game session, UI layout or binding behavior has been tested. Use upstream defaults first. Optional:
WoW-Pro minimap settings → **Main → Automation** off for deliberate quest dialogue; `/clnsettings`
checks voice packs. Keep TomTom/Waypoint UI defaults until you verify guide navigation.

## Maintenance and rollback

```sh
wow-addons list --format detailed
wow-addons sync
wow-addons update
systemctl --user list-timers wow-addons-update.timer
journalctl --user -u wow-addons-update.service
```

The instawow manifest is [wow-addons.json](wow-addons.json); deploy edits before `sync` uses them.
It never adopts/deletes WowUp-only addons. The existing **05:00 Europe/Berlin** persistent timer,
1/5/15-minute retries, terminal-only notification and WoW-running skips are retained. Close WoW before
interactive changes in either manager; do not launch it while writes are active. Keep WowUp auto-updates
off and update **only its non-ignored packages**, individually, while WoW is closed.

A complete private pre-change AddOns/WTF/database backup is recorded in [recovery](docs.md#backup-and-recovery).
[Technical notes](docs.md) own package/provider status; [VISION.md](VISION.md) describes future direction.

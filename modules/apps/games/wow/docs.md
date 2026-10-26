# WoW add-ons: sources, ownership and recovery

## Intentions and status

Manage supported release archives additively in the existing Retail installation. Preserve unmanaged
add-ons, WTF, existing ToxiUI profiles and global authentication. [`README.md`](README.md) owns
first-play steps; [`wow-addons.json`](wow-addons.json) owns desired packages; [`wow.nix`](wow.nix) owns
package/profile/timer integration.

**Main installation:** 37 additions plus three existing packages, followed by
Chatty Little NPC base v3.5.3, Vanilla English voices v3.3.4 and Midnight
English voices v1.2.11 = 43 managed.
All 37 passed disposable installation first; 92 trial folders were audited for
Retail compatibility. The bundled DBM-Party-Forever excludes Retail explicitly.
The full native `wow-addons update` completed with exit 0 across all 43 packages;
manifest/database equality passed. The AddOns directory contains 100 folders. All
64 existing WTF file hashes remained unchanged. Both voice-pack TOCs include
120105 and their required Chatty dependency was verified in installed files.
In-game behavior has not been tested. No settings were applied beyond upstream defaults; existing
ToxiUI was left untouched. Versions below are 2026-10-26 snapshots.
`Installed` means package installation, not runtime acceptance. `Blocked` means
no usable configured source.

## Package catalogue

Source cells link official projects; `github:` names their exact repositories. WoWInterface IDs are
exact native URIs. CurseForge/Wago catalogue availability does not establish download access: their
tokens are absent on this installation.

| Add-on / benefit | Source | Status |
|---|---|---|
| ElvUI / base interface | [tukui:elvui](https://github.com/tukui-org/ElvUI) | Existing managed setup |
| ToxiUI / coherent ElvUI theme | [github:Toxicom/toxiui](https://github.com/Toxicom/toxiui/releases) | Existing setup retained |
| WindTools / ElvUI extras | [github:wind-addons/ElvUI_WindTools](https://github.com/wind-addons/ElvUI_WindTools/releases) | Existing managed setup |
| WoW-Pro / guided quest progress | [github:Ludovicus-Maior/WoW-Pro-Guides](https://github.com/Ludovicus-Maior/WoW-Pro-Guides/releases) | Installed 20261016; requires TomTom |
| TomTom / waypoint service | [wowi:7032](https://www.wowinterface.com/downloads/info7032-TomTom.html) | Installed v4.3.13-release |
| Waypoint UI / navigation display | [github:Adaptvx/Waypoint-UI](https://github.com/Adaptvx/Waypoint-UI/releases) | Installed 1.7.4 |
| BtWQuests / quest-chain journal | [wowi:24680](https://www.wowinterface.com/downloads/info24680-BtWQuests.html) | Installed v2.65.0 |
| BtWQuests Midnight / current chains | Bundled by [wowi:24680](https://www.wowinterface.com/downloads/info24680-BtWQuests.html) | Installed v3.1; TOC 120105 |
| BtWQuests Prologue / expansion introductions | [wago:kNM3d3Kz](https://addons.wago.io/user/Breeni) | Blocked: Wago token |
| BtWQuests Dragonflight / legacy chains | [github:Breeni/BtWQuestsDragonflight](https://github.com/Breeni/BtWQuestsDragonflight/releases) | Installed v12.15 |
| BtWQuests TWW / legacy chains | [github:Breeni/BtWQuestsTheWarWithin](https://github.com/Breeni/BtWQuestsTheWarWithin/releases) | Installed v11.4 |
| BtWQuests Cataclysm / optional Tirisfal chains | [wowi:25552](https://www.wowinterface.com/downloads/info25552-BtWQuestsCataclysm.html) | Optional, not installed; disposable v2.23 passed, TOC 120105 |
| Dialogue UI / readable quest conversations | [github:Peterodox/YUI-Dialogue](https://github.com/Peterodox/YUI-Dialogue/releases) | Installed v1.0.6 |
| World Quest Tracker / world-quest overview | [wago:lQNlrEKe](https://addons.wago.io/addons/world-quest-tracker) | Blocked: Wago/CF token; old GitHub release has no asset |
| HandyNotes / map-pin framework | [github:Nevcairiel/HandyNotes](https://github.com/Nevcairiel/HandyNotes/releases) | Installed v1.6.31 |
| HandyNotes Midnight / treasures and rares | [github:kemayo/wow-handynotes-midnight](https://github.com/kemayo/wow-handynotes-midnight/releases) | Installed v73 |
| HandyNotes TWW / treasures | [github:kemayo/wow-handynotes-warwithin](https://github.com/kemayo/wow-handynotes-warwithin/releases) | Installed v112 |
| HandyNotes Dragonflight / treasures | [github:kemayo/wow-handynotes-dragonflight](https://github.com/kemayo/wow-handynotes-dragonflight/releases) | Installed v82 |
| HandyNotes Shadowlands / treasures | [github:kemayo/wow-handynotes-shadowlandstreasures](https://github.com/kemayo/wow-handynotes-shadowlandstreasures/releases) | Installed v101 |
| HandyNotes BFA / treasures | [github:kemayo/wow-handynotes-battleforazerothtreasures](https://github.com/kemayo/wow-handynotes-battleforazerothtreasures/releases) | Installed v46 |
| HandyNotes Legion / treasures | [github:kemayo/wow-handynotes-legiontreasures](https://github.com/kemayo/wow-handynotes-legiontreasures/releases) | Installed v56 |
| HandyNotes WoD / treasures | [github:kemayo/wow-handynotes-treasurehunter](https://github.com/kemayo/wow-handynotes-treasurehunter/releases) | Installed v50 |
| HandyNotes Pandaria / treasures | [github:kemayo/wow-handynotes-lostandfound](https://github.com/kemayo/wow-handynotes-lostandfound/releases) | Installed v53 |
| HandyNotes Wrath / treasures | [github:kemayo/wow-handynotes-wrath](https://github.com/kemayo/wow-handynotes-wrath/releases) | Installed v32 |
| HandyNotes BC / treasures | [github:kemayo/wow-handynotes-burningcrusade](https://github.com/kemayo/wow-handynotes-burningcrusade/releases) | Installed v26 |
| RareScanner / rare alerts | [curse:rarescanner](https://www.curseforge.com/wow/addons/rarescanner) | Blocked: CF token; 12.1.5.3 maintained |
| GatherMate2 / observed gathering nodes | [github:Nevcairiel/GatherMate2](https://github.com/Nevcairiel/GatherMate2/releases) | Installed 1.52.3 |
| GatherMate2_Data / seed gathering nodes | [github:Nevcairiel/GatherMate2_Data](https://github.com/Nevcairiel/GatherMate2_Data/releases) | Installed v41.0; manual import |
| Routes / gathering route planning | [github:Nevcairiel/Routes](https://github.com/Nevcairiel/Routes/releases) | Installed v1.8.7 |
| Leatrix Maps / optional map refinements | [curse:leatrix-maps](https://www.curseforge.com/wow/addons/leatrix-maps) | Blocked: CF token |
| All The Things / collection checklist | [github:ATTWoWAddon/AllTheThings](https://github.com/ATTWoWAddon/AllTheThings/releases) | Installed 5.4.5 |
| Krowi's Achievement Filter / achievement navigation | [github:TheKrowi/Krowi_AchievementFilter](https://github.com/TheKrowi/Krowi_AchievementFilter/releases) | Installed 104.0; TOC 120105 |
| Rarity: Collector's Edition / drop attempts | [github:aSnejbjerg/Rarity-Collectors-edition](https://github.com/aSnejbjerg/Rarity-Collectors-edition/releases) | Installed v0.3.1; maintained continuation |
| Home Bound / housing collection | [curse:home-bound](https://www.curseforge.com/wow/addons/home-bound) | Blocked: CF token; GitHub 1.13 is old TOC 110207 |
| Can I Mog It? / appearance overlays | [github:TorelTwiddler/CanIMogIt](https://github.com/TorelTwiddler/CanIMogIt/releases) | Installed 12.1.5-1 |
| Mount Journal Enhanced / mount filters | [github:exochron/MountJournalEnhanced](https://github.com/exochron/MountJournalEnhanced/releases) | Installed 2.56.1; TOC 120105 |
| Rematch / pet teams | [original distribution](https://www.curseforge.com/wow/addons/rematch) | Deferred: original 5.3.1 targets 12.0, known 12.1 breakage |
| DBM / encounter warnings | [github:DeadlyBossMods/DeadlyBossMods](https://github.com/DeadlyBossMods/DeadlyBossMods/releases) | Installed 12.1.17 |
| DBM Dungeons, Delves & Events / extra encounters | [github:DeadlyBossMods/DBM-Dungeons](https://github.com/DeadlyBossMods/DBM-Dungeons/releases) | Installed r268 |
| Details! / damage analysis | [curse:61284](https://www.curseforge.com/wow/addons/details) | Blocked: CF token; ancient GitHub release unusable |
| GTFO / audible hazard warning | [wowi:17996](https://www.wowinterface.com/downloads/info17996-GTFO.html) | Installed 6.12.2; Midnight detection restricted |
| Mythic Dungeon Tools / route planning | [github:Nnoggie/MythicDungeonTools](https://github.com/Nnoggie/MythicDungeonTools/releases) | Installed 6.3.23 |
| Raider.IO / group history information | [github:RaiderIO/raiderio-addon](https://github.com/RaiderIO/raiderio-addon/releases) | Installed v202610260600 |
| Premade Groups Filter / group selection | [github:0xbs/premade-groups-filter](https://github.com/0xbs/premade-groups-filter/releases) | Installed; correct official repo |
| WarpDeplete / Mythic+ timer | [github:Happenslol/WarpDeplete](https://github.com/Happenslol/WarpDeplete/releases) | Installed v5.4.4; declares 120100, player acceptance needed |
| Plumber / modular interaction conveniences | [github:Peterodox/Plumber](https://github.com/Peterodox/Plumber/releases) | Installed v1.9.7; TOC 120105/120107 |
| OPie / radial action menus | [curse:opie; official author](https://www.townlong-yak.com/addons/opie) | Blocked: CF token; no native alternate verified |
| LiteMount / contextual mount choice | [github:xod-wow/LiteMount](https://github.com/xod-wow/LiteMount/releases) | Installed 12.1.5-2 |
| Altoholic + DataStore / alt inventory | [curse:altoholic](https://www.curseforge.com/wow/addons/altoholic) | Blocked: CF token; current v12.1.007; inspect bundle before separate dependencies |
| SavedInstances / alt lockouts and resets | [github:SavedInstances/SavedInstances](https://github.com/SavedInstances/SavedInstances/releases) | Installed 12.1.0; TOC 120100 |
| Leatrix Plus / modular QoL | [curse:leatrix-plus](https://www.curseforge.com/wow/addons/leatrix-plus) | Blocked: CF token; 12.1.14 maintained |
| GuildFinder+ / guild discovery | [curse:guildfinder](https://www.curseforge.com/wow/addons/guildfinder) | Blocked: CF token |
| Better Fishing / one-key cast and interact | [wago:9rN4ZwKD](https://addons.wago.io/addons/better-fishing) | Blocked: Wago/CF token |
| BugGrabber / error capture | [wago:7x61oyG1](https://addons.wago.io/addons/buggrabber) | Blocked: Wago/CF token; official source is SVN |
| BugSack / error display | [github:funkydude/BugSack](https://github.com/funkydude/BugSack/releases) | Omitted: requires blocked BugGrabber |
| Ultimate Mouse Cursor / cursor visibility | [curse:ultimate-mouse-cursor](https://www.curseforge.com/wow/addons/ultimate-mouse-cursor) | Blocked: CF token; standalone addon, not old WeakAura |
| Narcissus / character and collection presentation | [github:Peterodox/Narcissus](https://github.com/Peterodox/Narcissus/releases) | Installed v1.8.7; bundled modules |
| DynamicCam / general world camera | [wago:b6XVoOGp](https://addons.wago.io/addons/dynamiccam) | Blocked: Wago/CF token; official GitHub has no release assets |
| TradeSkillMaster / economy operations | [curse:26886](https://www.curseforge.com/wow/addons/tradeskill-master) | Blocked: CF token; companion ownership unresolved |
| TSM_AppHelper / companion price data | [official companion setup](https://support.tradeskillmaster.com/tsm-desktop-application/how-do-i-set-up-the-tsm-desktop-application) | Deferred: no verified native URI; companion-owned mutable data |
| Chatty Little NPC / dialogue voice player | [github:mantaskazlauskas/ChattyLittleNpc](https://github.com/mantaskazlauskas/ChattyLittleNpc/releases) | Installed v3.5.3; voice packs separate |
| English Vanilla voice pack / old-world speech | [github:mantaskazlauskas/ChattyLittleNPC-Vanilla-Voiceovers](https://github.com/mantaskazlauskas/ChattyLittleNPC-Vanilla-Voiceovers/releases) | Installed v3.3.4; archive 1.29 GB |
| English Midnight voice pack / current speech | [github:mantaskazlauskas/ChattyLittleNPC-Midnight-english-voiceover-pack](https://github.com/mantaskazlauskas/ChattyLittleNPC-Midnight-english-voiceover-pack/releases) | Installed v1.2.11; archive 432 MB |

The two installed voice packs total **1,721,356,240 bytes** of compressed release assets (metadata
sizes). Native installs took 196 seconds for Vanilla and 73 seconds for Midnight. No other voice
expansions are included; playback/coverage remain player checks.

## Decisions and feature ownership

Prefer real official compatible GitHub release ZIPs, then supported WoWInterface, Wago/Tukui and
accessible CurseForge. Do not add dead manifest entries for missing tokens, custom downloaders or
repository-source ZIPs lacking packaged dependencies. Rarity CE replaces the original's stable TOC
110207 release with a maintained Midnight continuation. CanIMogIt GitHub's latest tag can be Forever;
select mainline releases. HomeBound's old GitHub release, unofficial Rematch patches and Leatrix 3.3.5
backports are not equivalent current official packages. One Kemayo HandyNotes family avoids duplicate
expansion pins; Zarillion's family is an alternative, not an extra layer.

ElvUI/ToxiUI owns frames, baseline layout and existing repair/sell automation; inspect actual in-game
values before enabling duplicate WindTools/Leatrix options. WoW-Pro owns guide progress, TomTom waypoint
data, Waypoint UI navigation, BtWQuests chain history, HandyNotes discovery pins and GatherMate2
gathering nodes. Select one visible objective tracker and damage meter after player inspection. Krowi
owns achievement navigation; Narcissus_Achievements may overlap, so review its native add-on toggle if a
conflict appears. Do not delete managed package subfolders.

Dialogue UI explicitly cooperates with DynamicCam; retain Dialogue UI NPC motion and use DynamicCam for
general situations only if later installed. DynamicCam's NPC Interaction situation 300 watches frames
replaced by Dialogue UI and cannot simply take over its camera. TomTom arrow hiding can clear Waypoint
UI's adopted target. Use Waypoint UI's **Appearance → Navigator → Show Arrow** off to retain TomTom's
arrow without Waypoint UI's extra arrow; verify guide progression in game. TomTom alpha is bounded to
0.1 and lower values reset to 1; no invisible-arrow workaround. Avoid `/wp` because both guide and
navigation add-ons register it.

Altoholic's official DataStore family covers core, Achievements, Agenda, Auctions, Characters,
Containers, Crafts, Currencies, Garrisons, Inventory, Mails, Pets, Quests, Reputations, Spells, Stats
and Talents (`curse:datastore` / `curse:datastore_NAME`). Check the official bundle/TOCs before
installing separately; CF relations alone lists no dependencies and does not establish bundle contents.

TSM's official desktop client supports Windows/Mac; Wine is reported usable but Linux unsupported.
Nix-capable community clients exist, including
[tsm-app-linux](https://github.com/exceptionptr/tsm-app-linux), without established TSM endorsement or
credential/security review. A separate trust/ownership decision must precede login or service
activation. [Official
guidance](https://support.tradeskillmaster.com/how-do-i-fix-an-error-about-appdatalua-being-empty) says
to ignore both TSM and AppHelper in other managers when companion-managed; AppHelper contains writable
prices. No companion, account setup or custom sync is provided.

## Optional native action bars

Export the current ElvUI profile first. `/ec` → **ActionBars → Player Bars → Bar 1** exposes
**Mouseover**, **Inherit Global Fade**, **Alpha**, **Visibility State** and **Action Paging**. Keep main
Mouseover off, utility Mouseover on, per-bar global fade inheritance off and Alpha 1; keep populated
bars enabled. Mouse-hide only genuine utilities; keep essential combat-cooldown bars visible until
native cooldown views are verified. Preserve visibility conditions, 12 slots, stance/pet/extra/zone bars and
native special states. Mouseover-hidden cooldowns are invisible until hovered; a paged main bar shows
only its current page's cooldowns. `/moveui` handles placement without replacing profiles.

The [README](README.md#optional-refinements) owns the optional paging steps. In installed
[ElvUI](https://github.com/tukui-org/ElvUI), native vehicle/override/temporary-shapeshift and manually
selected bar-state clauses precede the editable class string; the default page is appended afterward.
Preserve this priority. A custom unconditional catch-all in the editable string makes appended
modifier clauses unreachable; inspect rather than replacing it speculatively. Retaining Druid clauses
first protects native form pages but limits the example to the base/humanoid bar. Slots on pages 2/3
are shared with existing bars, not new independent action storage.

Paging changes display pages, **not modified-key bindings**. Ten existing Shift+number CLICK bindings
were observed in one private cache; no explicit Ctrl+number cache entries establish effective runtime
bindings. Preserve them until the player chooses otherwise. Mouseover-hidden utility cooldowns remain
invisible until hovered; the main bar shows only its current page's cooldowns. Actual hold/release,
modified casts, forms and vehicle/pet/extra/zone behavior need player acceptance. No settings,
bindings, actions or profile overrides have been applied by this work.

## Installation, updates and authentication

Retail root: `/home/v/Games/battlenet/drive_c/Program Files (x86)/World of Warcraft/_retail_`; packages
reside under `Interface/AddOns`. `wow-addons` selects `phoenix-retail` and serializes operations with a
one-hour-wait flock. Native commands need `instawow -p phoenix-retail`. The deployed manifest is
additive; explicit removal and adoption remain operator actions (`wow-addons remove SOURCE`, or
deliberately `wow-addons install --replace SOURCE` after backup). Never reconcile whole directories.

The daily 09:00 Europe/Berlin timer syncs then updates; Persistent catches missed runs without waking
the computer. Journal receives errors; service access masks unrelated home and exposes only AddOns, tool
config/cache/state and shared lock. No process check, signal, game start or reload occurs. Wait for
writes before a manual reload: loaded Lua is not hot-patched and mixed files can otherwise load. Large voice-package
resolution/update can take minutes and exceed 1 GB RAM (observed process RSS about 1.2 GB).

Instawow 7.3.0 is pinned in wow.nix because locked 7.0.0.post1 rejects catalogue `forever_classic`.
Upstream versioningit/wcwidth and Click 8.4.1 are supplied; aiohttp/rapidfuzz/yarl lower bounds are
relaxed against locked packages, with focused upstream tests and live checks. Revisit relaxations on
updates; remove the override when the locked package is verified. Do not update flake.lock incidentally.

The writable profile baseline is `~/.config/instawow/profiles/phoenix-retail/config.json`; `db.sqlite`
sits beside it. Home Manager reasserts profile/path; global credentials, DB/cache and rollback history
stay app-owned. GitHub OAuth is already configured: never repeat onboarding or replace it. New
installations only, with `umask 077`, use `instawow -p phoenix-retail profile configure
global_config.access_tokens.github`, then the native device flow at <https://github.com/login/device>.
Review consent; never paste tokens into chat, commands or Git. [GitHub
limits](https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api) and [OAuth
scopes](https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/scopes-for-oauth-apps) explain
public-data access and quotas. Linux tokens are plaintext in instawow `config.json`, with optional
`config.access_tokens.json`; preserve both if present, shared across profiles. Directory 0700/files
0600, owned by v; inspect debug redaction before sharing output. Credentials must never enter Nix or
Git.

## Settings portability and recovery

Use supported in-game controls; no direct WTF edits or generic import framework. Chatty's `/clnsettings`
→ **Playback** exposes **Auto-Play Voiceovers** (default on), **Quest Playback Mode** and **Gossip
Playback Mode** (default queues continuing after close), plus audio channel (default Master). Language
defaults to client locale with English fallback. **Installed Voiceover Packs** reports detected packs.
These defaults were checked in installed v3.5.3 source; playback was not tested. ElvUI: `/ec` →
**Profiles → Export Profile**; private configuration is separate. OPie: **Share ring** / **New Ring →
Import Snapshot** if installed. DynamicCam's published documentation does not establish a portable
sharing workflow. ToxiUI has no supported Blizzard Edit Mode export; use Blizzard's own Edit Mode
controls.

The pre-change private rollback point is
`~/.local/state/phoenix-wow/backups/collection-20261026T090133Z`: `retail-before.tar.gz` contains WTF
and AddOns; `instawow.sqlite` and `managed-before.json` retain manager state/inventory. The collection
installation did not modify saved settings.

For a full rollback, perform these steps in order; **no restore has been performed**:

1. Close WoW yourself. Stop scheduling and active package writes with `systemctl --user stop
   wow-addons-update.timer wow-addons-update.service`. Finish/stop any interactive `wow-addons` or
   `instawow` operation before continuing.
2. Create a new private recovery directory with `umask 077`. Move the current Retail `Interface/AddOns`
   and `WTF` directories there, preserving both whole directories. Also preserve the profile's current
   `db.sqlite` and, if present, `db.sqlite-wal` and `db.sqlite-shm`; move all three out of the profile
   directory. Keep the native profile and global credentials unchanged. Do not overlay an old database
   while leaving its newer WAL/SHM alongside it.
3. Inspect `retail-before.tar.gz`'s member paths and extract into a private staging directory. Restore
   its complete AddOns and WTF directories to the Retail paths above. Copy the backed-up
   `instawow.sqlite` to the profile as `db.sqlite` with owner v and mode 0600; preserve the original
   backup. Compare package inventory with `managed-before.json` and check SQLite integrity before
   running the manager.
4. Revert the collection's manifest commit/additions while preserving unrelated repository changes.
   Deploy the restored `wow-addons.json` before restarting the updater: `sync` reads the deployed
   immutable manifest and would otherwise reinstall removed packages. Avoid package update/sync during
   restoration.
5. Once files, database and deployed manifest agree, restart scheduling with `systemctl --user start
   wow-addons-update.timer`. Open WoW yourself and verify the restored interface/settings. Keep the
   moved-aside state until accepted.

For future backups, capture complete WTF privately plus manifest/revision, package versions and
supported exports. Stop writers or use SQLite's backup API for DB snapshots. Keep
account/realm/character mappings and credentials outside Git with restricted permissions; credentials
need a separate secret backup/onboarding choice.

A shareable preset needs per-add-on supported exports, compatible versions, ownership, import order and
manual steps. Inspect/sanitize identifiers, chat/social data and secrets, then test on a disposable
profile before calling it portable. Full WTF is private state, not a distributable preset. Package
success does not prove desktop, 4K readability, quest navigation, encounter warnings or voice behavior:
player checks remain required. Follow [scoped guidance](AGENTS.md) before future settings work.

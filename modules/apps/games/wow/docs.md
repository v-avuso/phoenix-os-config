# WoW packages, ownership and recovery

## Intentions and status

Preserve the existing Retail installation, private settings and instawow ownership. Two explicit
updaters now have different responsibilities: the desired instawow set is **68 packages** in
[`wow-addons.json`](wow-addons.json), including the original 58 and ten official English expansion voice packs.
The post-game removal workflow reduces the installed set from 69 to 68.
WowUp-CF is installed from locked Nixpkgs **2.22.0**, with only `wowup-cf` added to the existing
unfree allowlist. No custom AppImage wrapper or lock update was added.

**WowUp-CF owns sixteen packages** installed by the operator. Its `addons.json` and actual folders
were audited read-only: existing instawow rows are ignored with auto-update off; all sixteen CF rows
also have auto-update off. No CF package was reinstalled or adopted. The post-removal folder count is **151**.
The newer BtWQuests and English voice-pack records require Ignore reconciliation when discovered, as described in [README.md](README.md#maintenance). No application state was rewritten.

## Small utility batch audit — 2026-10-27

Hide Vendor Sell Price **12.1.0** (`github:delulunia/HideVendorSellPrice`, GitHub release,
folder `Interface/AddOns/HideVendorSellPrice`) failed the player's ElvUI/ToxiUI acceptance test:
the vendor price remains visible. Its source is removed from the 68-entry desired manifest.
The installed addon and database record must be removed only with WoW closed, after deploying
the 68-entry manifest. An old 69-entry deployed manifest would otherwise reinstall it.
Follow the [post-game cleanup](README.md#post-game-removal)
to deploy first, remove the managed record/files, and verify sync does not restore it.

Source inspection found the addon suppresses `TooltipDataLineType.SellPrice` and existing money
frames; ElvUI's `TT.AddMoneyInfo` handles the same line type and can add its own formatted text.
This explains a plausible overlap, not a proven runtime cause. No further tooltip rewrite,
replacement addon, settings change or authentication change is part of removal.

ObjectiveBarManager (`curse:1109979`) and DamageMeterKeybind (`curse:1492150`) remain **uninstalled**.
Both resolve in the current instawow catalogue, but native dry-run resolution reports
“package source is disabled: access token missing”. Bounded publisher/GitHub searches found no
usable alternative public release for these two; this is not proof of source exclusivity.
Their publisher pages advertise Retail 12.1.0 support. Exact release source, TOCs, dependencies,
installed folders and skin compatibility remain unaudited pending WowUp installation; no folder name
is asserted as an installed result. Keep them exclusively WowUp-owned if installed manually.

Private pre-install backup: `~/.local/state/phoenix-wow/backups/small-addons-20261027/`,
containing current customized WTF and a consistent instawow database. All 221 WTF files, 138,794
existing addon files, authentication configuration and WowUp state were fingerprinted and verified
unchanged after installation; only the three new addon files were added. Eight updater tests pass;
the opt-in native systemd fixture was skipped. Isolated native install, managed list and targeted
dry-run update pass (the native up-to-date result exits 1). The original 69-package manifest was subsequently deployed and verified. Removal uses the same normal deployment workflow, with WoW closed.
No authentication is copied
into Git. No WoW launch, profile changes, key assignment or service activation is part of this batch.

## Package catalogue

Installed rows are instawow-owned unless explicitly marked **WowUp-CF**; ownership includes bundled
folders. Separate expansion/prologue modules contain different content; Midnight remains bundled by core. Keep official dependencies with the same owner unless already owned
by instawow, in which case cancel replacement and resolve the collision. Snapshot: 2026-10-26.

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
| BtWQuests Midnight Prologue / expansion introduction | [wago:kNM3d3Kz](https://addons.wago.io/user/Breeni) | Blocked: Wago token; compatible published archive still unverified |
| BtWQuests Dragonflight / legacy chains | [github:Breeni/BtWQuestsDragonflight](https://github.com/Breeni/BtWQuestsDragonflight/releases) | Installed v12.15 |
| BtWQuests TWW / legacy chains | [github:Breeni/BtWQuestsTheWarWithin](https://github.com/Breeni/BtWQuestsTheWarWithin/releases) | Installed v11.4 |
| BtWQuests Cataclysm / optional Tirisfal chains | [wowi:25552](https://www.wowinterface.com/downloads/info25552-BtWQuestsCataclysm.html) | Installed v2.23; Retail TOC 120105 |
| Dialogue UI / readable quest conversations | [github:Peterodox/YUI-Dialogue](https://github.com/Peterodox/YUI-Dialogue/releases) | Installed v1.0.6 |
| World Quest Tracker / world-quest overview | [CurseForge](https://www.curseforge.com/wow/addons/world-quest-tracker) | **WowUp-CF** installed v12.1.5.561; auto-update off |
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
| RareScanner / rare alerts | [wago:kaNeng62](https://addons.wago.io/addons/rarescanner); [curse:rarescanner](https://www.curseforge.com/wow/addons/rarescanner) | **WowUp-CF** installed RareScanner_12.1.5.3; auto-update off |
| GatherMate2 / observed gathering nodes | [github:Nevcairiel/GatherMate2](https://github.com/Nevcairiel/GatherMate2/releases) | Installed 1.52.3 |
| GatherMate2_Data / seed gathering nodes | [github:Nevcairiel/GatherMate2_Data](https://github.com/Nevcairiel/GatherMate2_Data/releases) | Installed v41.0; manual import |
| Routes / gathering route planning | [github:Nevcairiel/Routes](https://github.com/Nevcairiel/Routes/releases) | Installed v1.8.7 |
| Leatrix Maps / optional map refinements | [curse:leatrix-maps](https://www.curseforge.com/wow/addons/leatrix-maps) | **WowUp-CF** installed 12.1.14; auto-update off |
| All The Things / collection checklist | [github:ATTWoWAddon/AllTheThings](https://github.com/ATTWoWAddon/AllTheThings/releases) | Installed 5.4.5 |
| Krowi's Achievement Filter / achievement navigation | [github:TheKrowi/Krowi_AchievementFilter](https://github.com/TheKrowi/Krowi_AchievementFilter/releases) | Installed 104.0; TOC 120105 |
| Rarity: Collector's Edition / drop attempts | [github:aSnejbjerg/Rarity-Collectors-edition](https://github.com/aSnejbjerg/Rarity-Collectors-edition/releases) | Installed v0.3.1; maintained continuation |
| Home Bound / housing collection | [curse:home-bound](https://www.curseforge.com/wow/addons/home-bound) | **WowUp-CF** installed HomeBound 1.61; auto-update off |
| Can I Mog It? / appearance overlays | [github:TorelTwiddler/CanIMogIt](https://github.com/TorelTwiddler/CanIMogIt/releases) | Installed 12.1.5-1 |
| Mount Journal Enhanced / mount filters | [github:exochron/MountJournalEnhanced](https://github.com/exochron/MountJournalEnhanced/releases) | Installed 2.56.1; TOC 120105 |
| Rematch / pet teams | [original distribution](https://www.curseforge.com/wow/addons/rematch) | Deferred: original 5.3.1 targets 12.0, known 12.1 breakage |
| DBM / encounter warnings | [github:DeadlyBossMods/DeadlyBossMods](https://github.com/DeadlyBossMods/DeadlyBossMods/releases) | Installed 12.1.17 |
| DBM Dungeons, Delves & Events / extra encounters | [github:DeadlyBossMods/DBM-Dungeons](https://github.com/DeadlyBossMods/DBM-Dungeons/releases) | Installed r268 |
| Details! / damage analysis | [wago:qv63A7Gb](https://addons.wago.io/addons/details-damage-meter-standalone); [curse:61284](https://www.curseforge.com/wow/addons/details) | **WowUp-CF** installed Details.20261015.15339.172; auto-update off |
| GTFO / audible hazard warning | [wowi:17996](https://www.wowinterface.com/downloads/info17996-GTFO.html) | Installed 6.12.2; Midnight detection restricted |
| Mythic Dungeon Tools / route planning | [github:Nnoggie/MythicDungeonTools](https://github.com/Nnoggie/MythicDungeonTools/releases) | Installed 6.3.23 |
| Raider.IO / group history information | [github:RaiderIO/raiderio-addon](https://github.com/RaiderIO/raiderio-addon/releases) | Installed v202610260600 |
| Premade Groups Filter / group selection | [github:0xbs/premade-groups-filter](https://github.com/0xbs/premade-groups-filter/releases) | Installed; correct official repo |
| WarpDeplete / Mythic+ timer | [github:Happenslol/WarpDeplete](https://github.com/Happenslol/WarpDeplete/releases) | Installed v5.4.4; declares 120100, player acceptance needed |
| Plumber / modular interaction conveniences | [github:Peterodox/Plumber](https://github.com/Peterodox/Plumber/releases) | Installed v1.9.7; TOC 120105/120107 |
| OPie / radial action menus | [curse:opie; official author](https://www.townlong-yak.com/addons/opie) | **WowUp-CF** installed 8.10.2; auto-update off |
| LiteMount / contextual mount choice | [github:xod-wow/LiteMount](https://github.com/xod-wow/LiteMount/releases) | Installed 12.1.5-2 |
| Altoholic + DataStore / alt inventory | [curse:altoholic](https://www.curseforge.com/wow/addons/altoholic) | Superseded by preferred Syndicator; not installed |
| SavedInstances / alt lockouts and resets | [github:SavedInstances/SavedInstances](https://github.com/SavedInstances/SavedInstances/releases) | Installed 12.1.0; TOC 120100 |
| Leatrix Plus / modular QoL | [curse:leatrix-plus](https://www.curseforge.com/wow/addons/leatrix-plus) | **WowUp-CF** installed 12.1.14; auto-update off |
| GuildFinder+ / guild discovery | [curse:guildfinder](https://www.curseforge.com/wow/addons/guildfinder) | **WowUp-CF** installed GuildFinderPlus-1.0.51.zip; auto-update off |
| Better Fishing / one-key cast and interact | [CurseForge](https://www.curseforge.com/wow/addons/better-fishing) | **WowUp-CF** installed 66; auto-update off |
| BugGrabber / error capture | [CurseForge](https://www.curseforge.com/wow/addons/bug-grabber) | **WowUp-CF** installed v12.1.1; auto-update off |
| BugSack / error display | [CurseForge](https://www.curseforge.com/wow/addons/bugsack) | **WowUp-CF** installed v12.1.8; auto-update off |
| Ultimate Mouse Cursor / cursor visibility | [curse:ultimate-mouse-cursor](https://www.curseforge.com/wow/addons/ultimate-mouse-cursor) | **WowUp-CF** installed Version 1.13.1; auto-update off |
| Narcissus / character and collection presentation | [github:Peterodox/Narcissus](https://github.com/Peterodox/Narcissus/releases) | Installed v1.8.7; bundled modules |
| DynamicCam / general world camera | [CurseForge](https://www.curseforge.com/wow/addons/dynamiccam) | **WowUp-CF** installed 2.21.5; auto-update off |
| TradeSkillMaster / economy operations | [curse:26886](https://www.curseforge.com/wow/addons/tradeskill-master) | **WowUp-CF** installed v4.14.78; auto-update off |
| TSM_AppHelper / companion price data | [official companion setup](https://support.tradeskillmaster.com/tsm-desktop-application/how-do-i-set-up-the-tsm-desktop-application) | Deferred: no verified native URI; companion-owned mutable data |
| Simple Addon Manager / searchable addon enablement and profiles | [github:Eliote/SimpleAddonManager](https://github.com/Eliote/SimpleAddonManager/releases/tag/v1.67) | Installed v1.67; TOC 120100; native install/update passed |
| BlizzMove / moving Blizzard windows | [github:Kiatra/BlizzMove](https://github.com/Kiatra/BlizzMove/releases/tag/v3.8.5) | Installed v3.8.5 through instawow; native WindTools deferral |
| Chatty Little NPC / dialogue voice player | [github:mantaskazlauskas/ChattyLittleNpc](https://github.com/mantaskazlauskas/ChattyLittleNpc/releases) | Installed v3.5.3; voice packs separate |
| English Vanilla voice pack / old-world speech | [github:mantaskazlauskas/ChattyLittleNPC-Vanilla-Voiceovers](https://github.com/mantaskazlauskas/ChattyLittleNPC-Vanilla-Voiceovers/releases) | Installed v3.3.4; archive 1.29 GB |
| English Midnight voice pack / current speech | [github:mantaskazlauskas/ChattyLittleNPC-Midnight-english-voiceover-pack](https://github.com/mantaskazlauskas/ChattyLittleNPC-Midnight-english-voiceover-pack/releases) | Installed v1.2.11; archive 432 MB |
| Syndicator / cross-character inventory without new bags | [curse:988370](https://www.curseforge.com/wow/addons/syndicator) | **WowUp-CF** installed 287; auto-update off |
| KeystoneLoot / dungeon and raid loot planning | [wowi:26597](https://www.wowinterface.com/downloads/info26597-KeystoneLoot.html) | Installed 2.19.0 through instawow |
| BtWQuests BC / Retail Outland chains | [wowi:25631](https://www.wowinterface.com/downloads/info25631.html) | Installed v4.25 |
| BtWQuests Wrath / Retail Northrend chains | [wowi:25784](https://www.wowinterface.com/downloads/info25784.html) | Installed v1.28 |
| BtWQuests MoP / Retail Pandaria chains | [wowi:25547](https://www.wowinterface.com/downloads/info25547.html) | Installed v4.23 |
| BtWQuests WoD / Retail Draenor chains | [wowi:25553](https://www.wowinterface.com/downloads/info25553.html) | Installed v3.22 |
| BtWQuests Legion / Retail chains | [wowi:24770](https://www.wowinterface.com/downloads/info24770.html) | Installed v30.23 |
| BtWQuests BFA / Retail chains | [wowi:25792](https://www.wowinterface.com/downloads/info25792.html) | Installed v53.31 |
| BtWQuests BFA Prologue | [wowi:24769](https://www.wowinterface.com/downloads/info24769.html) | Installed v15.22 |
| BtWQuests Shadowlands | [wowi:25655](https://www.wowinterface.com/downloads/info25655.html) | Installed v6.28 |
| BtWQuests Shadowlands Prologue | [wowi:25660](https://www.wowinterface.com/downloads/info25660.html) | Installed v1.24 |
| BtWQuests Dragonflight Prologue | [wowi:26458](https://www.wowinterface.com/downloads/info26458.html) | Installed v1.21 |
| BtWQuests TWW Prologue | [github:Breeni/BtWQuestsTheWarWithinPrologue](https://github.com/Breeni/BtWQuestsTheWarWithinPrologue/releases) | Installed v1.13 release; packaged TOC says 1.2 |
| OPie: ElvUI Skin | [wowi:26446](https://www.wowinterface.com/downloads/info26446.html) / [official GitHub](https://github.com/AcidWeb/OPie_ElvUI/releases) | Skipped v1.5.1: incompatible with installed OPie's Midnight API |

## English voice pack coverage

All ten requested additions use official `mantaskazlauskas` public GitHub release ZIPs through native
instawow; no custom downloader, duplicate pack, new credentials or WowUp-only installation was used.
The exact package name is the repository component after `github:mantaskazlauskas/` below.
All ten release and installed TOCs declare Retail 120105 and depend on the existing Chatty core.
Vanilla v3.3.4, Midnight v1.2.11 and base v3.5.3 remain unchanged. The existing ToxiUI profile and
all other installed packages are preserved.

| Exact package name / instawow source | Release | New AddOns folder |
|---|---|---|
| `github:mantaskazlauskas/ChattyLittleNPC-Cataclysm-english-voiceover-pack` | v3.2.6 | `ChattyLittleNpc_Cataclysm_voiceovers` |
| `github:mantaskazlauskas/ChattyLittleNPC-Battle-for-Azeroth-English-voiceover-pack` | v3.2.5 | `ChattyLittleNpc_Battle_for_Azeroth_voiceovers` |
| `github:mantaskazlauskas/ChattyLittleNPC-Dragonflight-English-voiceover-pack` | v3.2.5 | `ChattyLittleNpc_Dragonflight_voiceovers` |
| `github:mantaskazlauskas/ChattyLittleNPC-Legion-english-voiceover-pack` | v3.1.6 | `ChattyLittleNpc_Legion_voiceovers` |
| `github:mantaskazlauskas/ChattyLittleNPC-Mists-of-Pandaria-english-voiceover-pack` | v3.1.6 | `ChattyLittleNpc_Mists_of_Pandaria_voiceovers` |
| `github:mantaskazlauskas/ChattyLittleNPC-Shadowlands-English-voiceover-pack` | v3.2.6 | `ChattyLittleNpc_Shadowlands_voiceovers` |
| `github:mantaskazlauskas/ChattyLittleNPC-The-Burning-Crusade-english-voiceover-pack` | v3.2.8 | `ChattyLittleNpc_The_Burning_Crusade_voiceovers` |
| `github:mantaskazlauskas/ChattyLittleNPC-The-War-Within-English-voiceover-pack` | v3.2.6 | `ChattyLittleNpc_The_War_Within_voiceovers` |
| `github:mantaskazlauskas/ChattyLittleNPC-Warlords-of-Draenor-english-voiceover-pack` | v3.2.5 | `ChattyLittleNpc_Warlords_of_Draenor_voiceovers` |
| `github:mantaskazlauskas/ChattyLittleNPC-Wrath-Of-The-Lich-King-english-voiceover-pack` | v3.2.5 | `ChattyLittleNpc_Wrath_of_the_Lich_King_voiceovers` |

The release assets total **4,870,232,186 bytes compressed** (4.87 GB). About 3.1 TB was free before
and after installation. Native installs ran in two-pack batches; Cataclysm was prioritized. Its first
attempt hit a transient GitHub socket timeout; the normal native retry and every batch succeeded.
No source or downloader patch was introduced. The built 68-package manifest sync and NixOS build
pass. A representative Cataclysm dry-run update reports up to date (native targeted no-change
exit 1); no installed files were modified by that check.

The file audit checked every indexed entry: **179,548 audio references**, none missing, all with
recognized Ogg/MPEG headers. Some author-supplied `.ogg` files carry MPEG rather than Ogg headers;
bytes were retained exactly as published. Playback/coverage remain in-game checks, not a source-only
guarantee. `/clnsettings` exposes the installed packs; no voice preferences were reset or applied.

Each new folder above is instawow-owned. Set its package record to Ignore / Auto Update off when
WowUp discovers it. Keep Chatty core, Vanilla and Midnight ignored; the fifteen existing CF packages
stay WowUp-owned. The final ownership audit found no active overlap. No private WowUp state was edited.
All packs installed successfully, so no fallback WowUp package names are needed.

Voice-work backup: `~/.local/state/phoenix-wow/backups/first-play-20261026T210252Z` contains the pre-change 58-package
AddOns tree, consistent database, manifest and **current customized WTF**. All **221 WTF file hashes**
and GitHub credential configuration match that snapshot after installation. No in-game launch,
ToxiUI installer/profile change, bindings, action bars or other interface settings were touched.
For voice-only rollback, close WoW and both writers, remove only the ten new source URIs above through
instawow, restore/deploy the pre-change manifest and leave unchanged WTF alone. Preserve the backup.

## Updater ownership and safe use

The original 46 instawow package records are ignored with auto-updates off. The twelve additions
from `b7f39af` are still absent from WowUp's records and may need a rescan, then Ignore / Auto Update
off. The fifteen CurseForge package records must remain WowUp-managed. See the README's
[exact new-package lookup list](README.md#new-btwquests-packages--wowup-ignore-checklist).
Records and folders differ: 68 instawow + 15 WowUp packages account for 150 folders; core and Midnight
are one package with two folders. Recheck original protection after rescanning; do not bulk-ignore
the mixed-manager collection. In packaged v2.22.0, `onClickIgnoreAddons` sets
`autoUpdateEnabled=false` when ignoring. Its mixed-selection toggle can first clear flags; verify
fully checked Ignore and repeat if necessary. Do not use unrestricted Update All, adoption,
reinstallation or provider switching. Do not rescan casually: the [official guide](https://wowup.io/guide/my-addons/overview)
says scanning rebuilds WowUp's metadata; recheck protection afterward. New instawow packages also
require protection in WowUp. Conversely, never adopt WowUp-owned folders into instawow without an
explicit ownership transfer. The manifest is additive and removes no unmanaged folders.

WowUp's [client options](https://wowup.io/guide/options/wow-clients) support selecting the existing
`_retail_/Wow.exe`, stable channel and default auto-update off. This client is a supported free
CurseForge integration; the operator does not supply instawow CF/Wago API credentials. Provider terms,
consent and package availability still apply; no provider request was routed through a custom API.
Keep all WowUp automatic updates and autostart off for today's setup; update only its chosen,
non-ignored packages individually with WoW closed. Neither manager should touch the other's folders.

The existing instawow user service/timer remains **05:00 Europe/Berlin**, `Persistent=true`, with
60/300/900-second retry waits, one shared flock, terminal-only notification and safe WoW-running
skips. It updates only its database/manifest packages. No service logic, auth or schedule changed in
this workstream. Preflight checks do not lock the independent game launcher; do not launch during
writes. New addons can require reopening the game; never force a reload during writes.

### WowUp close preference

Packaged v2.22.0's [close handler](https://github.com/WowUp/WowUp.CF/blob/v2.22.0/wowup-electron/app/main.ts)
hides the window only when the stored collapse-to-tray preference is true; otherwise its final window
close leads to `app.quit()`. The supported persistent control is **Options → Application → Minimize
on Close → Off**, per the [official guide](https://wowup.io/guide/options/application). The local setting
was observed enabled. No external configuration interface was verified and the application's private
preference store was left untouched; the README records this remaining manual step.

## TSM and configuration ownership

The main TSM addon is installed; WowUp currently has Auto Update off but **Ignore is
not yet enabled**. Before the first companion sync, transfer update ownership by
ignoring both TSM and AppHelper in WowUp. No account setup or price-data sync has
been performed by this task.
The [official companion](https://support.tradeskillmaster.com/tsm-desktop-application/how-do-i-set-up-the-tsm-desktop-application)
normally owns both TSM and AppHelper and writes price data. Before companion takeover,
ignore **both** in other updaters, per [official guidance](https://support.tradeskillmaster.com/how-do-i-fix-an-error-about-appdatalua-being-empty).
Do not update AppHelper's mutable `AppData.lua` independently. Linux is
[officially unsupported](https://support.tradeskillmaster.com/en_US/tsm-desktop-application/can-i-run-the-tsm-desktop-application-on-linux);
the community client below is provided with that limitation.

`tsm-app.nix` pins [exceptionptr/tsm-app-linux](https://github.com/exceptionptr/tsm-app-linux/tree/60ad454b7187c3d2f1e4df36352b2af0fade02a6)
1.1.16 by revision and archive hash, reusing its official additive overlay against
our locked Nixpkgs. This avoids a second Qt/Python closure and changes no flake lock.
The overlay supplies APScheduler 4 because the app needs its prerelease API.
`tsm-startup.patch` adds only a per-launch tray override, preserving native config;
upstream's hardcoded `/usr/bin` desktop command is corrected to `wow-tsm`.
The native app already implements single-instance protection, tray operation and
SIGTERM cleanup. It offers AppHelper installation and automatically updates installed
TSM addons from its API; instawow must not manage either TSM addon once it owns them.
The direct instawow `curse:tradeskill-master_apphelper` dry-run failed with
**access token missing**; catalogue fuzzy matches were unrelated helpers.

`wow.nix` retains the existing Lutris desktop ID and game URI; Home Manager backs up
the previous user-created desktop entry. A user service keeps the watcher independent
of launcher exit. The desktop item is linked through `xdg.dataFile` at the original
local path: a profile-only `xdg.desktopEntries` item would be shadowed by Lutris's
existing user file. The service constrains cleanup to its own child/cgroup, independent
of the launcher. `tsm-session.sh`
uses the existing updater's WoW executable-name pattern, restricted to the current
UID, and observes all that user's Retail/Classic clients. It does not distinguish
Wine prefixes. A shared runtime flock preserves foreground process ownership;
native single-instance protection also handles a direct `tsm-app` invocation.
There is no recurring AI work: the idle watcher sleeps two seconds between local
process checks. Native companion sync stays at its upstream five-minute interval.
The service has no autostart target and is triggered only by this Battle.net entry.

Desktop notifications are disabled with native `notifications_enabled = false` in
`~/.config/tsm-app/config.toml`. The app's central notification method checks this
master switch before sending tray/OS notifications, including periodic data updates.
Home Manager's `tsmNotifications` activation uses `disable-tsm-notifications.py` to
change only this key, validate preserved TOML values, and retain a private one-time
`.before-notifications` backup. The config stays writable for native settings.
The current process caches settings; the preference takes effect on its next launch.

Polling is deliberate: two-second local process checks keep the watcher simple
across Battle.net's indirect Wine launch and independent exit. An exit notifier
could avoid repeated queries, but would need to discover and track the relevant
game processes across that handoff; the added lifecycle complexity is not justified
by the accepted delay. The watcher sleeps between checks and sends SIGTERM once
all matching WoW processes disappear. Polling contributes up to roughly two seconds
to detection, not a fixed five-to-ten-second shutdown timer. A game process can
outlive its visible window, and TSM then needs its own graceful cleanup time.
The player confirmed automatic startup and shutdown, observing about five to ten
seconds after closing WoW; the individual contributions have not been measured.

CraftSim uses `github:derfloh205/CraftSim` (official release **27.0.7**), supplying
only `CraftSim`. Its release TOC requires built-in `Blizzard_Professions` and optionally
integrates with existing TSM/Syndicator. Catalogue, release dry-run and isolated
installation succeeded before the managed installation. The desired manifest now
contains **69** packages. Newly discovered WowUp rows must remain Ignore / Auto Update
off; existing WowUp metadata was not edited. AppHelper installation, TSM account/realm
setup and first sync are player steps; automatic game lifecycle behavior has been
confirmed by the player as described above.

Verification: the `metal-4tb` system build, flake evaluation, all 14 focused fixtures
(including the isolated user-systemd updater test), and the packaged TSM `--self-test`
on Wayland passed. The sandbox cannot access the host Wayland socket; the self-test
was therefore run through supported sandbox escalation. No real game or companion
account session was started. The upstream full PySide6 closure adds Qt modules and
Clang/Shiboken dependencies (Clang alone about 864 MiB); using the overlay shares
existing dependencies but does not eliminate that runtime closure cost.

ElvUI/ToxiUI owns layout, bars, bags, nameplates, repairs/selling and current bindings. Syndicator is
the preferred inventory backend/search, without replacing bags; Altoholic/DataStore remains omitted.
BlizzMove owns Blizzard-frame movement: installed WindTools `MoveFrames:Initialize` detects loaded
BlizzMove, sets `StopRunning` and returns. This supported integration supersedes the earlier decision
to omit BlizzMove. First-login load ordering/behavior still needs player confirmation; the fallback is
WindTools → Misc → Move Frames off through its native UI, never a raw WTF edit.

WoW-Pro owns guides, TomTom waypoint data, Waypoint UI navigation, BtWQuests chain history,
HandyNotes pins, GatherMate2 gathering data; DBM owns boss warnings. Details/WQT/TSM are installed owners of their respective features. Retain one main objective tracker. Keep Leatrix Plus repair/junk/quest
automation disabled and select other optional modules individually. Dialogue UI owns NPC dialogue;
if adding DynamicCam, the README's conservative first-play choice disables Dialogue camera motion.

The operator has now completed ToxiUI's installer and customized the UI in game. No Phoenix
addon-specific configuration overrides, new ToxiUI profiles, action assignments, bindings, CVars
or SavedVariables have been programmatically applied. All README setup steps remain manual. Advanced native
paging and remapping are deferred until the working baseline is accepted. Existing Press and Hold
Casting is preserved; its native `ActionButtonUseKeyHeldSpell` checkbox is documented only as an
optional check. The [ElvUI installer framework](https://github.com/tukui-org/ElvUI/wiki/layout-installer-template)
remains an upstream option, not a new local framework. Private ElvUI exports can preserve layout;
bindings/CVars and account-specific data need the personal backup. Shared presets require supported,
sanitized exports and disposable-profile acceptance, not complete WTF in Git.

### BtWQuests and OPie skin compatibility

All twelve additions declare Retail TOC 120105 and require the installed BtWQuests core. BC/Wrath
packages here describe quests in **Retail**, not Classic-client addons. Core-bundled Midnight and the
existing Dragonflight/TWW packages were neither replaced nor duplicated. BFA/Shadowlands/Dragonflight/
TWW prologues are distinct author-supported modules. Midnight Prologue's separate official GitHub
resolver returns no installable files; its existing Wago entry requires unavailable access. It remains
skipped rather than using a source-only archive or mirror.

The skin's two official sources both resolve 1.5.1 (TOC 120005). More decisively, installed OPie 8.10.2
`UI/RingView.lua` explicitly downgrades its `elvui` API 4 constructor to 3 on Midnight because combat
cooldown rendering is missing; the Retail minimum is API 4. The skin's `SetCooldownDuration` is empty.
Its dependencies exist, but the integration is rejected by OPie itself. Do not force-enable/patch it;
retain the working built-in skin. No skin files were installed in the real game.

## Installation paths and authentication

Retail root: `/home/v/Games/battlenet/drive_c/Program Files (x86)/World of Warcraft/_retail_`.
Addons: `Interface/AddOns`; settings: `WTF`. Nothing duplicates or relocates game data.
`wow-addons` selects `phoenix-retail`; direct native commands use `instawow -p phoenix-retail`.
Profile/DB: `~/.config/instawow/profiles/phoenix-retail/{config.json,db.sqlite}`. Global config stays
app-owned, with existing GitHub OAuth preserved (directory 0700/file 0600). Never put tokens in Git/Nix.

Future new-machine GitHub onboarding only: `umask 077; instawow -p phoenix-retail profile configure
global_config.access_tokens.github`, open <https://github.com/login/device>, enter the generated
code and approve public-data access. This helps avoid unauthenticated API limits. Credentials are
plaintext in `~/.config/instawow/config.json` or optional `config.access_tokens.json`; keep them private.
Do not repeat authentication on this installation. Instawow Wago download tokens require separately
eligible membership according to 7.3 onboarding; developer upload keys are not equivalent. WowUp-CF
avoids requiring either token for the proposed CF collection.

Instawow 7.3.0 remains pinned because locked 7.0 rejects current catalogue flavour metadata. Its existing
Click/versioningit/wcwidth integration and bounded dependency relaxations remain unchanged; revisit
when the locked package catches up, without an incidental flake.lock update.

## Backup and recovery

Private pre-change backup: `~/.local/state/phoenix-wow/backups/first-play-20261026T161948Z`.
It preserves the **complete AddOns tree**, WTF, consistent `instawow.sqlite`, managed inventory and
manifest. Existing older private backups were retained. The game itself was not copied.

For this module-only rollback, close WoW and both updater writers, remove only the twelve new
manifest sources through instawow, restore/deploy the pre-change manifest, then resume scheduling.
The backup inventory identifies the original 46 packages; all fifteen CF packages must remain.
Unchanged WTF does not need restoration. WowUp ownership metadata is backed up separately too.

For full restoration: stop the WoW timer/service, preserve current AddOns/WTF/database separately,
then restore the backup's matching AddOns/WTF and `instawow.sqlite` as the profile's `db.sqlite`.
Move aside any newer `db.sqlite-wal`/`db.sqlite-shm` first; do not overlay a database with unrelated WAL.
Restore/deploy the matching manifest before restarting the timer. Keep global credentials unchanged.
After WowUp is used, preserve its own app state and package export too; reassess Ignore flags after
restoration. No restore was performed. Personal backups remain private; sanitized portable exports
and the [long-term UI vision](VISION.md) remain separate concerns.

## Validation and limits

The previous BtWQuests work verified actual installation and targeted updates for all twelve modules; current versions reported
up to date (native targeted no-change exit 1, not an ignored generic error). That audit matched all 58 manifest entries and preserved the prior 46 identities/versions.
The voice-pack additions now bring the manifest/database to 68, preserving every prior 58 package. The folder/TOC audit finds
no duplicate native ownership, missing required Retail dependencies or missing package folders.
DBM-Party-Forever is correctly excluded from Retail. Fifteen CF-owned rows cover their separate folders,
with no overlap with active instawow ownership. New BtW modules remain unregistered in WowUp until scan.
WTF, GitHub credential configuration and WowUp metadata stayed byte-identical.

Core, Midnight, Dragonflight and TWW are intact. Retail module installation does not establish quest
accuracy in game. NixOS build/manifest sync checks apply to the deployed desired set; no layout,
keybindings, settings, gameplay or account configuration was changed. No WoW launch occurred.

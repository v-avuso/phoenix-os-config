# WoW packages, ownership and recovery

## Intentions and status

Preserve the existing Retail installation, private settings and instawow ownership. Two explicit
updaters now have different responsibilities: instawow owns the **46 installed packages** in
[`wow-addons.json`](wow-addons.json), including the original 44 plus BlizzMove and KeystoneLoot.
WowUp-CF is installed from locked Nixpkgs **2.22.0**, with only `wowup-cf` added to the existing
unfree allowlist. No custom AppImage wrapper or lock update was added.

**WowUp-CF currently owns zero packages:** it was not launched, scanned or configured. Native GUI
control is unavailable, so the exact first-run protection and installation procedure is in
[README.md](README.md#manual-configuration--before-first-play). Pending rows below are not installed.
Never infer a successful CF download or Ignore setting from application installation alone.

## Package catalogue

Installed rows are instawow-owned, including all their bundled folders. Pending WowUp rows are the
proposed separate CF collection. Keep official dependencies with the same owner unless already owned
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
| BtWQuests Cataclysm / optional Tirisfal chains | [wowi:25552](https://www.wowinterface.com/downloads/info25552-BtWQuestsCataclysm.html) | Optional, not installed; disposable v2.23 passed, TOC 120105 |
| Dialogue UI / readable quest conversations | [github:Peterodox/YUI-Dialogue](https://github.com/Peterodox/YUI-Dialogue/releases) | Installed v1.0.6 |
| World Quest Tracker / world-quest overview | [CurseForge](https://www.curseforge.com/wow/addons/world-quest-tracker) | Pending WowUp-CF GUI; not installed |
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
| RareScanner / rare alerts | [wago:kaNeng62](https://addons.wago.io/addons/rarescanner); [curse:rarescanner](https://www.curseforge.com/wow/addons/rarescanner) | Pending WowUp-CF GUI; not installed |
| GatherMate2 / observed gathering nodes | [github:Nevcairiel/GatherMate2](https://github.com/Nevcairiel/GatherMate2/releases) | Installed 1.52.3 |
| GatherMate2_Data / seed gathering nodes | [github:Nevcairiel/GatherMate2_Data](https://github.com/Nevcairiel/GatherMate2_Data/releases) | Installed v41.0; manual import |
| Routes / gathering route planning | [github:Nevcairiel/Routes](https://github.com/Nevcairiel/Routes/releases) | Installed v1.8.7 |
| Leatrix Maps / optional map refinements | [curse:leatrix-maps](https://www.curseforge.com/wow/addons/leatrix-maps) | Pending WowUp-CF GUI; not installed |
| All The Things / collection checklist | [github:ATTWoWAddon/AllTheThings](https://github.com/ATTWoWAddon/AllTheThings/releases) | Installed 5.4.5 |
| Krowi's Achievement Filter / achievement navigation | [github:TheKrowi/Krowi_AchievementFilter](https://github.com/TheKrowi/Krowi_AchievementFilter/releases) | Installed 104.0; TOC 120105 |
| Rarity: Collector's Edition / drop attempts | [github:aSnejbjerg/Rarity-Collectors-edition](https://github.com/aSnejbjerg/Rarity-Collectors-edition/releases) | Installed v0.3.1; maintained continuation |
| Home Bound / housing collection | [curse:home-bound](https://www.curseforge.com/wow/addons/home-bound) | Pending WowUp-CF GUI; old GitHub archive unsuitable |
| Can I Mog It? / appearance overlays | [github:TorelTwiddler/CanIMogIt](https://github.com/TorelTwiddler/CanIMogIt/releases) | Installed 12.1.5-1 |
| Mount Journal Enhanced / mount filters | [github:exochron/MountJournalEnhanced](https://github.com/exochron/MountJournalEnhanced/releases) | Installed 2.56.1; TOC 120105 |
| Rematch / pet teams | [original distribution](https://www.curseforge.com/wow/addons/rematch) | Deferred: original 5.3.1 targets 12.0, known 12.1 breakage |
| DBM / encounter warnings | [github:DeadlyBossMods/DeadlyBossMods](https://github.com/DeadlyBossMods/DeadlyBossMods/releases) | Installed 12.1.17 |
| DBM Dungeons, Delves & Events / extra encounters | [github:DeadlyBossMods/DBM-Dungeons](https://github.com/DeadlyBossMods/DBM-Dungeons/releases) | Installed r268 |
| Details! / damage analysis | [wago:qv63A7Gb](https://addons.wago.io/addons/details-damage-meter-standalone); [curse:61284](https://www.curseforge.com/wow/addons/details) | Pending WowUp-CF GUI; not installed |
| GTFO / audible hazard warning | [wowi:17996](https://www.wowinterface.com/downloads/info17996-GTFO.html) | Installed 6.12.2; Midnight detection restricted |
| Mythic Dungeon Tools / route planning | [github:Nnoggie/MythicDungeonTools](https://github.com/Nnoggie/MythicDungeonTools/releases) | Installed 6.3.23 |
| Raider.IO / group history information | [github:RaiderIO/raiderio-addon](https://github.com/RaiderIO/raiderio-addon/releases) | Installed v202610260600 |
| Premade Groups Filter / group selection | [github:0xbs/premade-groups-filter](https://github.com/0xbs/premade-groups-filter/releases) | Installed; correct official repo |
| WarpDeplete / Mythic+ timer | [github:Happenslol/WarpDeplete](https://github.com/Happenslol/WarpDeplete/releases) | Installed v5.4.4; declares 120100, player acceptance needed |
| Plumber / modular interaction conveniences | [github:Peterodox/Plumber](https://github.com/Peterodox/Plumber/releases) | Installed v1.9.7; TOC 120105/120107 |
| OPie / radial action menus | [curse:opie; official author](https://www.townlong-yak.com/addons/opie) | Pending WowUp-CF GUI; official author ZIP also available |
| LiteMount / contextual mount choice | [github:xod-wow/LiteMount](https://github.com/xod-wow/LiteMount/releases) | Installed 12.1.5-2 |
| Altoholic + DataStore / alt inventory | [curse:altoholic](https://www.curseforge.com/wow/addons/altoholic) | Superseded by preferred Syndicator; not installed |
| SavedInstances / alt lockouts and resets | [github:SavedInstances/SavedInstances](https://github.com/SavedInstances/SavedInstances/releases) | Installed 12.1.0; TOC 120100 |
| Leatrix Plus / modular QoL | [curse:leatrix-plus](https://www.curseforge.com/wow/addons/leatrix-plus) | Pending WowUp-CF GUI; leave repair/sell automation off |
| GuildFinder+ / guild discovery | [curse:guildfinder](https://www.curseforge.com/wow/addons/guildfinder) | Pending WowUp-CF GUI; not installed |
| Better Fishing / one-key cast and interact | [CurseForge](https://www.curseforge.com/wow/addons/better-fishing) | Pending WowUp-CF GUI; not installed |
| BugGrabber / error capture | [CurseForge](https://www.curseforge.com/wow/addons/bug-grabber) | Pending WowUp-CF GUI; install before BugSack |
| BugSack / error display | [CurseForge](https://www.curseforge.com/wow/addons/bugsack) | Pending WowUp-CF GUI after BugGrabber; keep one owner for both |
| Ultimate Mouse Cursor / cursor visibility | [curse:ultimate-mouse-cursor](https://www.curseforge.com/wow/addons/ultimate-mouse-cursor) | Pending WowUp-CF GUI; standalone addon |
| Narcissus / character and collection presentation | [github:Peterodox/Narcissus](https://github.com/Peterodox/Narcissus/releases) | Installed v1.8.7; bundled modules |
| DynamicCam / general world camera | [CurseForge](https://www.curseforge.com/wow/addons/dynamiccam) | Pending WowUp-CF GUI; no GitHub release assets |
| TradeSkillMaster / economy operations | [curse:26886](https://www.curseforge.com/wow/addons/tradeskill-master) | Pending WowUp-CF GUI; main addon only for today |
| TSM_AppHelper / companion price data | [official companion setup](https://support.tradeskillmaster.com/tsm-desktop-application/how-do-i-set-up-the-tsm-desktop-application) | Deferred: no verified native URI; companion-owned mutable data |
| Simple Addon Manager / searchable addon enablement and profiles | [github:Eliote/SimpleAddonManager](https://github.com/Eliote/SimpleAddonManager/releases/tag/v1.67) | Installed v1.67; TOC 120100; native install/update passed |
| BlizzMove / moving Blizzard windows | [github:Kiatra/BlizzMove](https://github.com/Kiatra/BlizzMove/releases/tag/v3.8.5) | Installed v3.8.5 through instawow; native WindTools deferral |
| Chatty Little NPC / dialogue voice player | [github:mantaskazlauskas/ChattyLittleNpc](https://github.com/mantaskazlauskas/ChattyLittleNpc/releases) | Installed v3.5.3; voice packs separate |
| English Vanilla voice pack / old-world speech | [github:mantaskazlauskas/ChattyLittleNPC-Vanilla-Voiceovers](https://github.com/mantaskazlauskas/ChattyLittleNPC-Vanilla-Voiceovers/releases) | Installed v3.3.4; archive 1.29 GB |
| English Midnight voice pack / current speech | [github:mantaskazlauskas/ChattyLittleNPC-Midnight-english-voiceover-pack](https://github.com/mantaskazlauskas/ChattyLittleNPC-Midnight-english-voiceover-pack/releases) | Installed v1.2.11; archive 432 MB |
| Syndicator / cross-character inventory without new bags | [curse:988370](https://www.curseforge.com/wow/addons/syndicator) | Pending WowUp-CF GUI; preferred over Altoholic |
| KeystoneLoot / dungeon and raid loot planning | [wowi:26597](https://www.wowinterface.com/downloads/info26597-KeystoneLoot.html) | Installed 2.19.0 through instawow |

## Updater ownership and safe use

Before any WowUp install, select all pre-existing Retail rows (including bundled/unknown modules),
set Ignore and verify Auto Update off. In packaged v2.22.0, `onClickIgnoreAddons` sets
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

## TSM and configuration ownership

The main TSM addon can be installed through WowUp-CF for today, without live desktop price data.
The [official companion](https://support.tradeskillmaster.com/tsm-desktop-application/how-do-i-set-up-the-tsm-desktop-application)
normally owns both TSM and AppHelper and writes price data. Before a future companion takeover,
ignore **both** in other updaters, per [official guidance](https://support.tradeskillmaster.com/how-do-i-fix-an-error-about-appdatalua-being-empty).
Do not update AppHelper's mutable `AppData.lua` independently. Linux is
[officially unsupported](https://support.tradeskillmaster.com/en_US/tsm-desktop-application/can-i-run-the-tsm-desktop-application-on-linux);
no community client, account setup or TSM authorization was attempted.

ElvUI/ToxiUI owns layout, bars, bags, nameplates, repairs/selling and current bindings. Syndicator is
the preferred inventory backend/search, without replacing bags; Altoholic/DataStore remains omitted.
BlizzMove owns Blizzard-frame movement: installed WindTools `MoveFrames:Initialize` detects loaded
BlizzMove, sets `StopRunning` and returns. This supported integration supersedes the earlier decision
to omit BlizzMove. First-login load ordering/behavior still needs player confirmation; the fallback is
WindTools → Misc → Move Frames off through its native UI, never a raw WTF edit.

WoW-Pro owns guides, TomTom waypoint data, Waypoint UI navigation, BtWQuests chain history,
HandyNotes pins, GatherMate2 gathering data; DBM owns boss warnings. Details/WQT/TSM are intended
owners once installed. Retain one main objective tracker. Keep Leatrix Plus repair/junk/quest
automation disabled and select other optional modules individually. Dialogue UI owns NPC dialogue;
if adding DynamicCam, the README's conservative first-play choice disables Dialogue camera motion.

No UI profiles, action assignments, bindings, CVars or SavedVariables were changed. Advanced native
paging and remapping are deferred until the working baseline is accepted. Existing Press and Hold
Casting is preserved; its native `ActionButtonUseKeyHeldSpell` checkbox is documented only as an
optional check. The [ElvUI installer framework](https://github.com/tukui-org/ElvUI/wiki/layout-installer-template)
remains an upstream option, not a new local framework. Private ElvUI exports can preserve layout;
bindings/CVars and account-specific data need the personal backup. Shared presets require supported,
sanitized exports and disposable-profile acceptance, not complete WTF in Git.

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

Private pre-change backup: `~/.local/state/phoenix-wow/backups/first-play-20261026T153808Z`.
It preserves the **complete AddOns tree**, WTF, consistent `instawow.sqlite`, managed inventory and
manifest. Existing older private backups were retained. The game itself was not copied.

For today's two-addon rollback, close WoW and both updater writers, remove
`github:Kiatra/BlizzMove` and `wowi:26597` through instawow, restore the prior manifest and deploy it
before resuming sync. This does not require restoring unchanged WTF.

For full restoration: stop the WoW timer/service, preserve current AddOns/WTF/database separately,
then restore the backup's matching AddOns/WTF and `instawow.sqlite` as the profile's `db.sqlite`.
Move aside any newer `db.sqlite-wal`/`db.sqlite-shm` first; do not overlay a database with unrelated WAL.
Restore/deploy the matching manifest before restarting the timer. Keep global credentials unchanged.
After WowUp is used, preserve its own app state and package export too; reassess Ignore flags after
restoration. No restore was performed. Personal backups remain private; sanitized portable exports
and the [long-term UI vision](VISION.md) remain separate concerns.

## Validation and limits

Original 44-package all-update and sandbox/retry/catch-up tests passed in the previous workstream.
Today's native source resolution and actual installation succeeded for BlizzMove and KeystoneLoot;
both declare TOC 120105, targeted native update probes report up to date (expected status 1 for
targeted no-change results), and all 46 manifest identities match. Original 44 identities/versions,
all 64 WTF hashes and the credential configuration remain unchanged. The complete private backup
contains the original 101 addon folders. Focused updater fixtures and
NixOS build checks validate the unchanged integration. WowUp GUI startup, Ignore flags and CF
downloads are **not tested**. No WoW launch, profile reset, binding change or in-game validation.

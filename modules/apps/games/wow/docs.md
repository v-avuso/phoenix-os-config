# WoW add-ons: sources, ownership and recovery

## Intentions and status

Manage supported release archives additively in the existing Retail installation. Preserve unmanaged
add-ons, WTF, existing ToxiUI profiles and global authentication. [`README.md`](README.md) owns
first-play steps; [`wow-addons.json`](wow-addons.json) owns desired packages; [`wow.nix`](wow.nix) owns
package/profile/timer integration.

**Main installation:** 37 additions plus three existing packages, followed by
Chatty Little NPC base v3.5.3, Vanilla English voices v3.3.4 and Midnight
English voices v1.2.11, plus Simple Addon Manager v1.67 = 44 managed.
All 37 passed disposable installation first; 92 trial folders were audited for
Retail compatibility. The bundled DBM-Party-Forever excludes Retail explicitly.
The original full native `wow-addons update` completed with exit 0 across all 43 packages;
manifest/database equality passed. The original AddOns directory contained 100 folders. All
64 existing WTF file hashes remained unchanged. Both voice-pack TOCs include
120105 and their required Chatty dependency was verified in installed files.
Follow-up: Simple Addon Manager passed isolated and actual installation (TOC 120100). Its
targeted update check reports up to date; native instawow returns status 1 for that targeted result.
All-package updates filter ordinary up-to-date results instead; the scheduler deliberately supplies no
package arguments. No arbitrary status-1 errors are swallowed.
The follow-up full 44-package sync/update passed inside the declared sandbox with status 0
(4m38s, 5.3 GB peak). All 44 manifest entries match managed identities; there are 101 addon folders.
All 64 WTF files and global credential configuration remained byte-identical. Backup SQLite integrity
and archive paths passed inspection; no restore or in-game test was performed.
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
| BtWQuests Midnight Prologue / expansion introduction | [wago:kNM3d3Kz](https://addons.wago.io/user/Breeni) | Blocked: Wago token; compatible published archive still unverified |
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
| RareScanner / rare alerts | [wago:kaNeng62](https://addons.wago.io/addons/rarescanner); [curse:rarescanner](https://www.curseforge.com/wow/addons/rarescanner) | Blocked: both require missing tokens; 12.1.5.3 maintained |
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
| Details! / damage analysis | [wago:qv63A7Gb](https://addons.wago.io/addons/details-damage-meter-standalone); [curse:61284](https://www.curseforge.com/wow/addons/details) | Blocked: both require missing tokens; GitHub release has no asset |
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
| Simple Addon Manager / searchable addon enablement and profiles | [github:Eliote/SimpleAddonManager](https://github.com/Eliote/SimpleAddonManager/releases/tag/v1.67) | Installed v1.67; TOC 120100; native install/update passed |
| BlizzMove / moving Blizzard windows | [github:Kiatra/BlizzMove](https://github.com/Kiatra/BlizzMove/releases/tag/v3.8.5) | Compatible TOC 120105; omitted because WindTools already provides moving frames |
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

## Native UI overrides and key ownership

No offline settings edits, custom preset addon or inert override file were added. The
[README](README.md#native-action-bar-preset-out-of-combat) contains the operational one-time procedure.
The official [ElvUI installer template](https://github.com/tukui-org/ElvUI/wiki/layout-installer-template)
supports profiles/installers, but a full wizard adds lifecycle/versioning/testing work and reloads the UI.
Native controls plus two explicit binding commands are cheaper for this small set of overrides.
ElvUI profile exports preserve the layout; Blizzard bindings and CVars require the private backup or
repeating the documented commands. No permanent process reasserts player preferences.

| Feature | Owner / non-default application |
|---|---|
| Base layout, bars, bags, nameplates, repairs/selling | Existing ElvUI/ToxiUI profile; native `/ec`/`/moveui` only |
| Blizzard window movement, ElvUI extensions | WindTools; no second mover or broad QoL suite |
| Main bar / utility visibility | User applies native per-bar fade/mouseover controls; preserve cooldown visibility |
| Shift/Ctrl action pages | Prepend two native paging conditions to the existing class string; retain form clauses |
| Numeric modified bindings | User-invoked native `SetBinding`/`SaveBindings`; main Shift/Ctrl, pets Ctrl+Shift; Alt reserved |
| Press-and-hold casting | Native Combat checkbox / `ActionButtonUseKeyHeldSpell=1`; no raw WTF edits |
| Quest automation | WoW-Pro defaults changed manually off so Dialogue UI owns story interaction |
| Navigation | TomTom data + Waypoint UI presentation; native destination replacement is a player choice |
| General camera | Native game defaults until DynamicCam available; Dialogue UI owns NPC interactions |
| World quests, economy, damage analysis | WQT, TSM, Details intended owners, currently provider blocked |
| Boss warnings | DBM, no BigWigs |
| Addon enablement / troubleshooting | Simple Addon Manager, no second disk updater |

Installed ElvUI `AB:GetPage` places override, vehicle/possess, temporary shapeshift, manually selected
pages 2–6 and bonusbar 5 ahead of the editable class string, then appends default page 1. Preserve this
native priority. Prepending Shift/Ctrl clauses enables them in ordinary Druid forms; releasing restores
the retained form page. This deliberately supersedes class-specific modifier clauses while held.
Pages 2/3 are shared action storage, not empty independent bars; the player assigns spells. Alt prevents
these modifier pages. Ctrl+Shift remains a pet shortcut even when the main bar displays Shift's page.

The static private audit found ten explicit Shift-numeric CLICK assignments, no explicit Ctrl-numeric
or Ctrl+Shift-numeric assignments in one cache. Inherited defaults and runtime overrides remain
unknown. The user authorizes replacing modifier bindings; high-frequency main casts take Shift/Ctrl,
pet commands move to Ctrl+Shift numeric keys. ElvUI reads `ACTIONBUTTON1..12` for main buttons and
`BONUSACTIONBUTTON1..10` for pets and redirects their bindings to its visible secure buttons. Essential
movement/base/Alt bindings are untouched. Source inspection cannot prove effective runtime bindings.

Blizzard-authored [Combat settings source](https://github.com/Gethe/wow-ui-source/blob/live/Interface/AddOns/Blizzard_SettingsDefinitions_Frame/Combat.lua)
registers `ActionButtonUseKeyHeldSpell`; Accessibility mirrors it. `ActionButtonUseKeyDown` controls
press/release activation and `empowerTapControls` controls empowered-spell input; neither is changed.
The repository is a source mirror, not proof the installed game build behaves identically. Hold/release,
modified casts, forms, pet/vehicle/extra/zone actions and combat behavior remain in-game acceptance.

## Provider access and recovery options

A renewed bounded scan found legitimate Wago alternatives for **Details** (`wago:qv63A7Gb`, also
identified by the [author TOC](https://github.com/Tercioo/Details-Damage-Meter/blob/master/Details.toc)) and
**RareScanner** (`wago:kaNeng62`). WQT remains `wago:lQNlrEKe`. Actual native dry-runs for these three and
`curse:26886` (TSM) all fail explicitly with **access token missing**; they were not installed. Compatible
stable release selection must still be tested after access exists. The catalogue does not index every
Wago project, so absence from search is not proof a source is unavailable.

Instawow 7.3's native onboarding says consumer Wago download tokens are issued to eligible **Patreon
subscribers**, pointing to [Wago Patreon login](https://addons.wago.io/patreon). No free self-service
consumer token route was verified; current tier/price could not be established from the public page.
[Wago developer upload keys](https://docs.wago.io/) serve a different API and are not a substitute.
If the operator independently chooses eligible membership, obtains a token and consents to storage,
configure it privately through the native masked prompt (not executed here):

```sh
umask 077
instawow -p phoenix-retail profile configure global_config.access_tokens.wago_addons
```

This global field shares existing app-owned credential storage and permissions described below.
No token belongs in arguments, chat, Nix or Git. After onboarding, resolve/install in a disposable profile
before adding the successful URI to the manifest. This would also unlock investigation of Better Fishing,
BugGrabber (then BugSack), DynamicCam and other Wago entries in the table; it does not guarantee
all packages are published/compatible. Midnight Prologue's official GitHub has no releases and its
Wago archive remains unverified even with a token.

For CF-only entries, instawow requires an operator-provided CurseForge Core API key; native prompt:
`instawow -p phoenix-retail profile configure global_config.access_tokens.cfcore`.
[CurseForge's official console](https://console.curseforge.com/) owns key eligibility/approval and
publisher download permissions still apply. No key application or subscription was initiated. Leatrix,
Home Bound, Altoholic/DataStore, GuildFinder+, Ultimate Mouse Cursor and TSM have no verified current
native token-free alternative from this scan. Original Rematch remains compatibility-deferred.
Official publisher/CurseForge project pages may also offer browser ZIP downloads without a new
account where the publisher permits them. That is a legitimate manual fallback, but it would require
manual updates and must stay outside the managed manifest until native resolution works. No such
unmanaged installation or second updater was added here.
BugSack alone is installable but not useful without BugGrabber. Do not install source-only repositories,
private-server backports or unauthorised mirrors as substitutes.

[OPie](https://www.townlong-yak.com/addons/opie) has a legitimate current direct author download,
but that host is not a native instawow provider. A manual author installation would require separate
maintenance; it was left out rather than adding a custom downloader. The installed collection is usable
without any of these accounts. Syndicator, KeystoneLoot and Simulationcraft remain future candidates.

TSM's simplest supported companion is its official Windows/macOS application; an operator-reviewed
Wine trial is possible, but [Linux is explicitly unsupported](https://support.tradeskillmaster.com/en_US/tsm-desktop-application/can-i-run-the-tsm-desktop-application-on-linux).
Community Linux clients remain unreviewed and are not installed. A future companion trial needs
explicit trust/login approval and **one owner** for TSM/AppHelper updates and mutable pricing, per the
official guidance above. No TSM credentials were requested.

## Installation, updates and authentication

Retail root: `/home/v/Games/battlenet/drive_c/Program Files (x86)/World of Warcraft/_retail_`; packages
reside under `Interface/AddOns`. `wow-addons` selects `phoenix-retail` and serializes operations with a
one-hour-wait flock. Native commands need `instawow -p phoenix-retail`. The deployed manifest is
additive; explicit removal and adoption remain operator actions (`wow-addons remove SOURCE`, or
deliberately `wow-addons install --replace SOURCE` after backup). Never reconcile whole directories.

The daily **05:00 Europe/Berlin** persistent timer runs one serialized `scheduled-update` invocation.
A small shell loop retries failed sync/update sequences after 60, 300 and 900 seconds; native
`RestartSteps` interpolates delays and does not express this exact sequence. Success stops immediately;
final failure retains its exit status and native `OnFailure` starts one local notification service.
No success/skip notifications. Journal logs attempts, waits, skips and command errors; the updater's
existing home masking exposes only AddOns/tool paths. The notification service separately uses the
user desktop bus, without exposing it to the network updater.

Exact case-insensitive WoW executable-name checks precede sync and update and every retry. Running
Retail (or conservatively Classic) is a successful skip, not a retryable failure. Detection errors fail
closed. A game starting after preflight remains a launch race: this does not interpose on Lutris or
provide an atomic launcher lock. Do not start WoW during active writes. A skip itself is not a missed
timer event and waits for the next scheduled/manual run. `Persistent` catches missed calendar events
when the user manager returns; it does not wake the computer.

Focused checks: `python3 -B -m unittest discover -s modules/apps/games/wow/tests -v`.
The opt-in native fixture uses `PHOENIX_WOW_SYSTEMD_TEST=1` and disposable user units: success,
transient failure, four terminal failures with status 23 and exactly one stub notification, running-game
skip with the fake process left alive, and real persistent-timer catch-up all pass. Stubs avoid network,
real package writes, 21-minute waits and desktop notification spam. This establishes systemd delivery
to the notification command, not visual desktop acceptance. Full native package updates can take
minutes; the previous 43-package service run observed a 5.4 GB peak, largely voice metadata.

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

The follow-up private backup `~/.local/state/phoenix-wow/backups/followup-20261026T125010Z`
contains `wtf-before.tar.gz`, a consistent `instawow.sqlite`, inventory and manifest. Only Simple Addon
Manager was added; no settings were changed. For this follow-up alone, close WoW, stop updater writes,
remove `github:Eliote/SimpleAddonManager` through instawow, restore the previous manifest/revision and
deploy it. Keep the archived WTF for optional recovery after in-game changes. Never restore a database
without restoring matching package files, and preserve current state first.

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

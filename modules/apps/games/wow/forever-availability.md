# Forever add-on availability

## Intentions

Use the shared Retail manifest for Forever when a source can select a compatible
release. Preserve independent add-on folders, package databases and WowUp ownership.
Source resolution is evidence of a matching release, not proof of in-game behavior.

## Follow-up source checks (2026-11-11)

- [TomTom](https://www.curseforge.com/wow/addons/tomtom) and
  [GTFO](https://www.curseforge.com/wow/addons/gtfo) publish shared Retail/Forever
  archives. A disposable Forever profile installed their WoWInterface releases
  v4.4.1-release and 6.12.3 without credentials. The extracted TomTom TOC declares
  interface 16001 and GTFO contains a 16001 Camelot TOC. This is package evidence,
  not an in-game test. The daily sync includes TomTom as a narrow exception based
  on its shared archive; the WoWInterface resolver does not validate future
  downloads, so a future packaging change may require intervention. GTFO remains
  excluded pending a decision about its usefulness.
- [BtWQuests](https://www.curseforge.com/wow/addons/btw-quests/files/9547866)
  has a distinct Forever v2.70.0-forever release with Forever quest data. Its
  WoWInterface Retail source returns a different, Retail-only release; use the
  Forever release through WowUp-CF if desired. No account/API key was added.
- [KeystoneLoot](https://www.wowinterface.com/downloads/info26597-KeystoneLoot.html)
  describes Retail Mythic+ and related loot, so it is not an obvious Forever fit.
  The twelve skipped BtWQuests expansion/prologue packages likewise describe later
  expansions. Their absence should not be interpreted as a broken core package.
- GatherMate2 itself is installed. Its optional pre-collected data and Routes
  remain unresolved for Forever; [SimpleRoutes for GatherMate2](https://www.curseforge.com/wow/addons/simpleroutes-for-gathermate2)
  is a distinct Forever-targeted alternative, not a verified replacement or an
  installed package. Krowi's Achievement Filter, SavedInstances and Mount Journal
  Enhanced have no matching release in the original source check; whether those
  features matter in Forever is a player decision.

WowUp-CF 2.24.1 added [Forever support](https://github.com/WowUp/WowUp.CF/releases/tag/v2.24.1).
The Nix configuration uses this release from locked unstable Nixpkgs, but actual
Forever client discovery and package selection still need a player check. It may
manage GTFO and BtWQuests there independently of their Retail InstaWoW records. If WowUp
discovers any Forever packages owned by InstaWoW,
set those records to Ignore / Auto Update off before package writes. Do not assume
that the selected manager has been configured or that add-ons work in game.

## Resolution snapshot (2026-11-11)

The pinned InstaWoW 7.3.0 was run with a disposable Forever profile and existing
GitHub authentication. These sources resolved a matching release (20):

- `tukui:elvui`
- `github:Toxicom/toxiui`
- `github:wind-addons/ElvUI_WindTools`
- `github:Ludovicus-Maior/WoW-Pro-Guides`
- `github:Adaptvx/Waypoint-UI`
- `github:Peterodox/YUI-Dialogue`
- `github:Nevcairiel/HandyNotes`
- `github:Nevcairiel/GatherMate2`
- `github:ATTWoWAddon/AllTheThings`
- `github:aSnejbjerg/Rarity-Collectors-edition`
- `github:TorelTwiddler/CanIMogIt`
- `github:DeadlyBossMods/DeadlyBossMods`
- `github:DeadlyBossMods/DBM-Dungeons`
- `github:Peterodox/Plumber`
- `github:xod-wow/LiteMount`
- `github:Peterodox/Narcissus`
- `github:Eliote/SimpleAddonManager`
- `github:mantaskazlauskas/ChattyLittleNpc`
- `github:mantaskazlauskas/ChattyLittleNPC-Vanilla-Voiceovers`
- `github:Kiatra/BlizzMove`

The following sources returned **no matching release** (35). This does not prove an
add-on has no Forever release on another source or that it can never work:

- `github:Breeni/BtWQuestsDragonflight`
- `github:Breeni/BtWQuestsTheWarWithin`
- `github:Breeni/BtWQuestsTheWarWithinPrologue`
- `github:kemayo/wow-handynotes-midnight`
- `github:kemayo/wow-handynotes-warwithin`
- `github:kemayo/wow-handynotes-dragonflight`
- `github:kemayo/wow-handynotes-shadowlandstreasures`
- `github:kemayo/wow-handynotes-battleforazerothtreasures`
- `github:kemayo/wow-handynotes-legiontreasures`
- `github:kemayo/wow-handynotes-treasurehunter`
- `github:kemayo/wow-handynotes-lostandfound`
- `github:kemayo/wow-handynotes-wrath`
- `github:kemayo/wow-handynotes-burningcrusade`
- `github:Nevcairiel/GatherMate2_Data`
- `github:Nevcairiel/Routes`
- `github:TheKrowi/Krowi_AchievementFilter`
- `github:exochron/MountJournalEnhanced`
- `github:Nnoggie/MythicDungeonTools`
- `github:RaiderIO/raiderio-addon`
- `github:0xbs/premade-groups-filter`
- `github:Happenslol/WarpDeplete`
- `github:SavedInstances/SavedInstances`
- `github:mantaskazlauskas/ChattyLittleNPC-Midnight-english-voiceover-pack`
- `github:mantaskazlauskas/ChattyLittleNPC-Cataclysm-english-voiceover-pack`
- `github:mantaskazlauskas/ChattyLittleNPC-Battle-for-Azeroth-English-voiceover-pack`
- `github:mantaskazlauskas/ChattyLittleNPC-Dragonflight-English-voiceover-pack`
- `github:mantaskazlauskas/ChattyLittleNPC-Legion-english-voiceover-pack`
- `github:mantaskazlauskas/ChattyLittleNPC-Mists-of-Pandaria-english-voiceover-pack`
- `github:mantaskazlauskas/ChattyLittleNPC-Shadowlands-English-voiceover-pack`
- `github:mantaskazlauskas/ChattyLittleNPC-The-Burning-Crusade-english-voiceover-pack`
- `github:mantaskazlauskas/ChattyLittleNPC-The-War-Within-English-voiceover-pack`
- `github:mantaskazlauskas/ChattyLittleNPC-Warlords-of-Draenor-english-voiceover-pack`
- `github:mantaskazlauskas/ChattyLittleNPC-Wrath-Of-The-Lich-King-english-voiceover-pack`
- `github:derfloh205/CraftSim`
- `github:myu-westfall/MyusKnowledgePointsTracker`

The following WoWInterface sources were **not checked by this resolver probe** (15).
See the follow-up above for subsequent TomTom, GTFO, BtWQuests and KeystoneLoot
checks. The resolver returns the Retail download and cannot select Forever files;
only TomTom is admitted to sync as a verified shared-archive exception:

- TomTom (`wowi:7032`)
- BtWQuests (`wowi:24680`)
- BtWQuests: Battle for Azeroth Prologue (`wowi:24769`)
- BtWQuests: Legion (`wowi:24770`)
- BtWQuests: Mists of Pandaria (`wowi:25547`)
- BtWQuests: Cataclysm (`wowi:25552`)
- BtWQuests: Warlords of Draenor (`wowi:25553`)
- BtWQuests: The Burning Crusade (`wowi:25631`)
- BtWQuests: Shadowlands (`wowi:25655`)
- BtWQuests: Shadowlands Prologue (`wowi:25660`)
- BtWQuests: Wrath of the Lich King (`wowi:25784`)
- BtWQuests: Battle for Azeroth (`wowi:25792`)
- BtWQuests: Dragonflight Prologue (`wowi:26458`)
- GTFO (`wowi:17996`)
- KeystoneLoot (`wowi:26597`)

Phoenix WoW Toolkit's Forever manifest includes its shared foundation and opt-in
ElvUI hold-to-cast adapter. Its other Retail features are not loaded there until
individually checked and ported. In-game testing remains necessary. WowUp-owned
packages are managed separately and are not included in this audit.

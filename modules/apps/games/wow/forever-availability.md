# Forever add-on availability

## Intentions

Use the shared Retail manifest for Forever when a source can select a compatible
release. Preserve independent add-on folders, package databases and WowUp ownership.
Source resolution is evidence of a matching release, not proof of in-game behavior.

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

The following WoWInterface sources were **not checked** (15). The pinned resolver
always returns the Retail download and cannot reliably select Forever files, so the
Forever sync excludes this source until a verified alternative is available:

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

Phoenix WoW Toolkit remains Retail-only: its TOC targets Retail, and feature APIs and
settings need a Forever compatibility review. Porting and in-game testing are follow-up
work. WowUp-owned packages are managed separately and are not included in this audit.

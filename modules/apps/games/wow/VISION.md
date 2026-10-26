# Phoenix UI Pack — North Star

## Intentions

Phoenix UI Pack aims to deliver a radically improved, cohesive WoW Retail user experience—not merely
a list of installed addons. A playable, reliable interface today takes precedence over this roadmap.
ToxiUI remains the present visual foundation; this document authorizes no additional implementation.

## Desired experience

Curate high-quality, actively maintained addons primarily for functionality and player experience,
then integrate them into a modern, visually consistent whole. Favor a clean bottom-heavy layout,
readable 4K scaling, clear combat information and unobstructed exploration. Assign each major feature
one owner; review competing trackers, tooltips, movers, camera behavior and keybindings together.
When shortcuts collide, prioritize frequent, valuable controls while retaining essential movement,
combat, class and pet functionality.

Install and update the complete compatible collection automatically. Apply supported settings through
native profiles, documented APIs and explicit one-time installation, rather than replacing mutable
SavedVariables wholesale. Minimize accounts, authentication, manual setup and ongoing maintenance.
Preserve existing settings, private data, rollback and player choice. Configuration updates should be
opt-in, reviewable and reversible, independently of routine package updates.

Eventually, a standalone graphical installer could coordinate package/source access, native profile
imports, ownership checks and recovery. An optional in-game integration addon could apply narrowly
supported settings and identify live conflicts. Portable, sanitized presets should accompany the
manifest; complete personal backups remain private. Neither installer nor generic configuration
framework is part of today's implementation.

## Reuse before building

- [Wago UI Packs](https://uipacks.wago.io/) illustrates coordinated packages and in-game profile updates;
  provider access and creator subscriptions remain separate usability costs.
- [LuckyoneUI](https://uipacks.wago.io/pack/luckyoneui) and [NaowhUI](https://naowh.gg/naowhui) offer
  integration/layout references, not replacements to install over the existing ToxiUI profile.
- [ElvUI's layout installer framework](https://github.com/tukui-org/ElvUI/wiki/layout-installer-template)
  supplies a native path when a real tested preset warrants an installer. A simple profile export or
  a few native controls is preferable while sufficient.
- [WowUp collection import/export](https://wowup.io/guide/my-addons/addon-import) distributes addon
  lists; that alone does not transfer settings, bindings or action assignments.

Periodically revisit upstream releases, native game features and integration opportunities. Prefer
removing redundant machinery to growing a compatibility layer. Consider small upstream contributions
when a missing documented API is the main obstacle to reliable integration. Add capabilities only
when a representative end-to-end trial demonstrates less player effort and acceptable maintenance.

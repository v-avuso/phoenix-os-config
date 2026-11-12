# WoW-Pro button bar

## Intentions

Respect WoW-Pro's own disabled button-bar setting after startup or a UI reload.
The Toolkit switch controls only this reconciliation; it does not choose whether
the user wants the bar visible or change unrelated WoW-Pro settings.

## Behavior and validation

`/pwt` → **Extensions** → **Fix hidden WoW-Pro button bar** defaults on. When
WoW-Pro's profile explicitly disables its bar, the feature asks WoW-Pro's
`HideAndSeek` method to hide it and applies the same layout refresh as WoW-Pro's
settings callback. It checks on activation, world entry, after WoW-Pro's guide-load
message, twice during delayed startup, and after combat. It never changes frames
in combat, polls continuously, or forces the bar hidden when WoW-Pro's setting is on.
Disabling this fix stops future reconciliation without changing the user's preference.

The installed WoW-Pro 2026.11.08.A uses the same `HideAndSeek` interface in both
clients. The fixture covers the saved preference, delayed initialization, combat
and disable. In-game acceptance: disable WoW-Pro's button bar, reload, wait for
its initialization, and check that the bar stays hidden; enable the WoW-Pro bar
and verify it remains visible. Check after combat and inspect BugSack for errors.

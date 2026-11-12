# ElvUI hold-to-cast

## Intentions

Let Forever players opt into Blizzard's press-and-hold casting on compatible ElvUI
action bars with one switch. Preserve normal casting, existing bindings and the
standalone Retail fix; do not simulate repeated input or make persistent key changes.

## Usage and limits

Enable Blizzard's **Press and Hold Casting**, then `/pwt` → **Extensions** →
**Fix ElvUI hold-to-cast**. The default is off. This first version is only loaded
on Forever and yields if the separate `HoldToCastFix` add-on is loaded. Retail
continues to use that add-on independently.

The routing targets ElvUI bars 1, 3–6 and 13–15 where the corresponding Blizzard
bindings exist; bars 2 and 7–10 use ElvUI-only bindings and are not covered. The
native casting feature itself may not repeat all kinds of actions. Vehicle,
possession and modifier-only page changes temporarily return bar 1 to ElvUI;
after returning in combat, restoration waits for combat to end. There is no
per-frame polling. This has not yet been validated in the Forever client.

## Approach and acceptance

Adapted from [ElvUI HoldToCastFix 1.9.0](https://github.com/danielbehrens/ElvUI-HoldToCastFix),
whose MIT license is included here. It uses high-priority temporary native binding
overrides and a secure state driver rather than synthetic repeating clicks. The
upstream add-on is Retail-only, has its own settings and is maintained separately;
this targeted adapter supplies one switch and Forever packaging. Its secure-state
and ActionBarController behavior depend on Blizzard and ElvUI internals, so upstream
changes can require adjustment.

Mocks exercise binding ownership, combat deferral, paging conditions and the
standalone-add-on conflict. After authorized deployment, test on a safe target:
normal and held casts on bar 1, another supported bar, modifier keys, shapeshifts,
vehicles, combat transitions, rebinding, and disabling the option. Confirm that
bindings still trigger the same actions; `/reload` after a bad result and disable
the feature out of combat. Tests do not establish protected execution or taint safety.

# OPie hidden quick actions

In Retail Phoenix WoW Toolkit settings, **Enable hidden quick actions** defaults
on and is available with the local OPie 8.10.4 adapter. In OPie's ring editor,
turn on **Allow as quick action** for an existing slice, then enter
`hide-active` as its visibility conditional. A conditional such as
`[combat] hide-active; show` hides it and enables center release in combat,
while drawing it as an ordinary slice outside combat.

On rings opened with their regular binding, the first qualifying hidden action
in ring order takes the center slot. Hold the key to open and release at center
to use it. The number and layout of directional slices depend on the other
visible entries. The adapter leaves OPie's on-open actions, animations,
directional selection and macro execution in place. Explicit hidden actions
are kept outside the positive directional indices and outside the renderer.
The checkbox gates execution for subsequent openings and always leaves the
marked slice hidden. Plain `hide`, action-level visibility, and the interaction
mode's pointer requirements still apply. Hidden nested collections and slices
embedded from other rings do not qualify.

The adapter changes three exact OPie files. The editor preserves bare `hide-active`. ActionBook collects the first eligible
hidden action separately from the visible collection, and the core makes it
available to its restricted center-release path. The original project stores
ordinary quick actions as visible slice tokens, so a companion alone cannot
supply the hidden action. The Toolkit only supplies the opt-in setting and
defers setting updates until combat ends.

[OPie user guide](https://www.townlong-yak.com/addons/opie/guide)

## Staging and checks

Stage a private copy from the installed Retail OPie tree, outside the game:

```sh
trial=$(mktemp -d)
python3 features/opie-center-release/stage-opie.py "/path/to/installed/OPie" "$trial/OPie"
lua features/opie-center-release/tests/secure.lua "$trial/OPie"
```

The fixture uses excerpts from the staged ActionBook and OPie core. It checks that the editor preserves bare `hide-active` and exercises
open without dispatch, primary release, all eight directions, plain hide,
multiple matches, ineligible slices, cancellation, checkbox off, and stock
quick/on-open actions. WoW frames and macro execution are simulated. In the client,
check a held ring, then release at center and in each direction. Repeat with a
combat-usable macro in combat and confirm no taint or blocked-action errors.

OPie updates can overwrite the adapter. The staging tool refuses changed source
hashes. Keep an unmodified copy for rollback. Before reverting to stock OPie,
replace `hide-active` with `hide` in your ring conditions, since the stock
visibility evaluator can treat the unknown keyword as visible. Neither the
adapter nor the Toolkit changes any saved rings or bindings automatically.

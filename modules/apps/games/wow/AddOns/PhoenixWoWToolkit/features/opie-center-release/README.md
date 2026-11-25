# OPie center-release feasibility fixture

This offline fixture checks whether OPie's secure release path can dispatch a
center action outside the directional sequence. It never registers a ring in the
Toolkit or changes installed add-ons or saved variables.

## Installed source findings

- `CustomRings.lua` translates **Allow as quick action** into a presentation-mode
  bit. `Libs/ActionBook/ActionBook.lua` evaluates action and token visibility
  before allocating contiguous directional indices. A hidden slice therefore
  has no index for the quick-action lookup in `OPieCore.lua`.
- **Use first slice when opened** removes the first slice from the direction
  sequence and emits it as `__openAction`. OPie dispatches that separate action
  on open. It has no public property for a separate center-release action.
- The fixture stages a private copy of reviewed OPie 8.10.4 core and renderer
  files and supplies a separate center action to the simulated ring. An index
  below zero keeps the eight-direction sequence length intact. The existing
  ActionBook path still handles macro dispatch. This demonstrates the secure
  path, while a production patch must resolve the intended hidden quick action
  from the existing ring and preserve other slices' visibility behavior.

[OPie user guide](https://www.townlong-yak.com/addons/opie/guide)

## Run offline

From the Toolkit directory, use an installed Retail OPie tree as the input:

```sh
trial=$(mktemp -d)
python3 features/opie-center-release/tests/stage-opie.py "/path/to/installed/OPie" "$trial/OPie"
lua features/opie-center-release/tests/secure.lua "$trial/OPie/OPieCore.lua"
```

The fixture checks open and repeat-down, center release, eight angles, the
neutral band, cancellation, and stock on-open and quick-action behavior.
Blizzard's protected runtime, combat and animations require in-client acceptance
of a production patch. Keep the staged copy private. OPie updates require
reinspecting the patched files and updating their reviewed hashes.

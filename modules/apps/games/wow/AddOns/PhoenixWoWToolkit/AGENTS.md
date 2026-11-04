# Standalone Retail add-on guidance

## Intentions and boundaries

- Keep this directory portable as its own repository. Feature behavior, docs,
  dependency research and tests belong in `features/<name>/`; core owns only the
  registration/persistence/settings contract and shared test runner.
- Use lowercase kebab-case for source directories and `phoenix-wow-toolkit` for a
  future extracted repository. Preserve the installed `PhoenixWoWToolkit` folder/TOC.
- Preserve feature IDs and SavedVariables keys across file moves. Use the public
  versioned registration API described in README; avoid core feature-name switches.
- Prefer native APIs and maintained upstream extension points. OPie is a separately
  authorized, version-pinned internal adapter; that authorization does not extend
  private hooks to unrelated add-ons. Never copy third-party proprietary code/assets.
- Gate permanent hooks when disabled and restore only owned visual state. Do not
  alter secure input, bindings, protected attributes or global CVars for cosmetics.
  Skip forbidden/secret inputs rather than attempting to bypass their boundaries.
- Keep Settings player-facing. Use short checkbox subtitles/tooltips, not research
  or implementation explanations. Compatible sections can share the same title.

## Verification

- Run `python3 tests/run.py --lua /path/to/lua`; upstream-backed proofs use explicit
  `--opie` / `--comparison-source` arguments and never modify their supplied sources.
- Test each feature independently and with the bundle. Preserve Objective Tracker's
  accepted behavior during refactors. Local fakes do not prove combat/taint safety.
- Tooltip regressions must include Show on an already-visible tooltip, hidden pooled
  text with stale content, and camera application after asynchronous model loading.
  Passing fake-layout tests never establishes the in-game visual result.
- An immutable installed package does not follow working files. Deployment and
  reload/restart are separate steps; neither a reload nor restart installs edits.
- PhoenixOS packaging/activation and its tests are owned outside this directory.
  Never activate or restart services just to validate these sources.

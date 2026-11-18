# Standalone add-on guidance

## Intentions and boundaries

- Keep this directory portable as its own repository. Feature behavior, docs,
  dependency research and tests belong in `features/<name>/`; core owns only the
  registration/persistence/settings contract and shared test runner.
- Use lowercase kebab-case for source directories and `phoenix-wow-toolkit` for a
  future extracted repository. Preserve the installed `PhoenixWoWToolkit` folder/TOC.
- Preserve feature IDs and SavedVariables keys across file moves. Use the public
  versioned registration API described in README; avoid core feature-name switches.
- Forever uses its Camelot TOC; list features there only after checking their client
  compatibility, since Retail feature and Settings APIs may not be available.
- Prefer native APIs and maintained upstream extension points. OPie is a separately
  authorized, version-pinned internal adapter; that authorization does not extend
  private hooks to unrelated add-ons. Never copy third-party proprietary code/assets.
- Keep integrations working across dependency updates when the interfaces they use
  still work. Validate the capabilities and behavior each integration relies on;
  use release strings for diagnostics. Pin an exact version only when a concrete
  compatibility or safety constraint cannot be checked reliably at runtime, and
  document that constraint at the adapter.
- Keep the native path usable until the optional integration succeeds. On an
  incompatible interface or runtime failure, restore owned UI state, disable only
  the affected integration, and expose the reason in its diagnostic.
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
  Include inventory-style hide/clear/rebuild/show in one frame as well as genuine
  leaves; a stable bank hover does not exercise inventory refresh ownership.
  Queued annotation refreshes must also respect current native visibility: a late
  AddLine followed by Hide must not cancel release or resurrect the replacement.
  Include stale/frozen frame dimensions and cached/internal Show/SetShown calls:
  suppression cannot depend on an observed size delta or propagate a masked source's
  alpha to its replacement. Exercise item/summon ownership transitions before another
  renderer samples native opacity. Cover native SetAction's spell/macro and opaque
  mount/pet routes; a journal setter alone does not establish action-bar coverage.
  Cover raw DataTextTooltip and native aura setters: data postcalls alone do not
  establish framing coverage. When masking a native tooltip, test attached child
  tooltips as well as embedded rows: child panels inherit the masked parent alpha.
  Preserve provider modifier rules, panel chains and restore ownership on release.
  Include theme-provider decorations such as ToxiUI's
  shadow/noise surfaces in suppression and restoration tests. Passing fakes never establishes the in-game visual result.
- Test a compatible dependency with unfamiliar metadata, a missing required
  capability, and failure after partial setup. Verify native fallback and cleanup.
  Upstream fixtures must preserve full installed metadata, including release suffixes.
- For actual Dialogue UI tooltip reuse, read the item feature's `research/README.md`
  first. The original renderer reuse proof supersedes the assumption that absence of
  a supported global API requires a new renderer. Keep singleton ownership and
  item-aware dispatch intact; do not extend the imitation before a live reuse trial.
  Mirrored data must retain TooltipDataType.Item and semantic price rows; exercise the
  real Blizzard comparison constructor, not a permissive fake accepting any table.
- An immutable installed package does not follow working files. Deployment and
  reload/restart are separate steps; neither a reload nor restart installs edits.
- Frame discovery must tolerate small client dimension rounding; exact `SetSize`
  inputs need not round-trip through `GetSize`. Identify protected notification
  frames independently of their current parent and reject ambiguous matches.
  Treat enumerated frame methods as potentially overridden: Blizzard damage-meter
  entries return a FontString from `GetName`; validate types before string operations.
- PhoenixOS packaging/activation and its tests are owned outside this directory.
  Never activate or restart services just to validate these sources.
- For native AuraSlots, initialize owned visuals in `initializeFrame`, before
  Blizzard applies button access restrictions. Spell catalog existence does not
  prove a hidden aura is assignable; validate aura identity and composition in the
  client before expanding integrations. Never infer aura state from slot visibility.

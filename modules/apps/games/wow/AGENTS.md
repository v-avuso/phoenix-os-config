# World of Warcraft add-on management

## Intentions and boundaries

- Own package installation, the additive manifest and WoW-specific integration here.
  Keep game files in the existing Lutris installation and preserve unrelated add-ons,
  WTF, profiles and global GitHub authentication. Never start a new OAuth flow for
  an already authenticated installation or print tokens/debug credential payloads.
- `README.md` owns first-play workflows; `docs.md` owns technical sources, resolved
  paths, status, and settings decisions. `wow.nix` owns integration, `default.nix`
  is the directory import, and `wow-addons.json` owns desired packages. `VISION.md` describes future direction,
  not current implementation.
  Keep the 05:00 Europe/Berlin timer dedicated to package updates, never settings.
  Scheduled runs must skip successfully when WoW is running, retain bounded retries
  and notify only on terminal failure. Preserve the single shared update lock.
- Addon-manifest tasks include deployment through the normal Phoenix workflow and
  post-deployment verification of the installed manifest, unless explicitly requested
  otherwise. A repository edit or successful sync alone does not update the deployed manifest.
- After package/source changes, test the actual current catalogue (`quest` search),
  official release resolution, isolated installation, and managed sync/list/update.
  An enum-only release fix does not establish catalogue compatibility. Prefer a
  supported upstream release to accumulating metadata compatibility patches.
  Search official publisher pages/TOCs too: catalogue absence does not establish
  source exclusivity (Wago projects may be missing from the catalogue).
- Keep the scheduled network updater restricted to its AddOns and tool data paths.
  `ProtectSystem` alone limits writes but still permits reading unrelated home data;
  retain home masking and verify both updater success and unrelated-path denial.

## Future add-on configuration

- Before changing settings, research official documentation, version compatibility,
  built-in configuration interfaces, supported files and portable profile exports.
  Inventory existing choices; assign each overlapping feature an explicit add-on
  owner and explain recommendations/tradeoffs before disabling redundant features.
- Prefer built-in interfaces and supported exports. Use direct configuration files
  only with a verified format and narrowly scoped edits. Never edit WTF while WoW
  is running; check process state first and stop dependent work if uncertain. Do
  not restart the game or force `/reload` to validate configuration.
- Back up affected settings privately before modification. Preserve unrelated values,
  account/realm/character mappings, private data and existing profiles. Validate
  restore/import on a disposable profile where possible, then request player checks.
- Record durable configuration decisions, responsibility ownership, compatible
  versions, import order and required manual steps in the owning documentation.
  Add per-add-on exports/scripts only for concrete requirements with a reliable,
  tested mechanism; do not build a generic importer/exporter speculatively.
- Distinguish two future deliverables: a complete private personal backup/restore
  procedure, and a sanitized portable preset plus declarative manifest. Private
  WTF files and credentials never belong in Git. Inspect exports for identifiers,
  social/chat data and secrets and test sanitization before describing them as
  shareable. Keep personal backups outside the repository with restricted access.

- Preserve the boundary between instawow and WowUp-CF: existing instawow packages,
  including bundled modules, must be ignored with auto-updates off in WowUp before
  any package writes. Rescans/new instawow installs require verifying that protection
  again. Never claim GUI flags/downloads are configured from installing the app alone.
- Check upstream integration before removing an apparent overlap: installed WindTools
  MoveFrames detects BlizzMove and defers to it. Keep native ElvUI special-state
  priority and distinguish paging from bindings; baseline play takes priority over
  an untested preset. No automatic keybinding remapping without a concrete later task.

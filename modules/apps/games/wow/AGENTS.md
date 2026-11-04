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
  For slow unchanged GitHub releases, inspect HTTP range behavior before adding
  concurrency: a 501 suffix-range response can trigger full voiceover ZIP downloads.
  Keep timeout cancellation confined to network work, never native file/DB writes.
- Addon-manifest tasks include deployment through the normal Phoenix workflow and
  post-deployment verification of the installed manifest, unless explicitly requested
  otherwise. A repository edit or successful sync alone does not update the deployed manifest.
- Build/check `nixosConfigurations.metal-4tb` for WoW integration: the generic
  `metal` target succeeds with this module disabled. Confirm the expected package
  and user units are present before treating a system build as WoW validation.
- When replacing a Lutris launcher, manage its existing `xdg.dataFile` path:
  `xdg.desktopEntries` alone installs a package entry that the local file shadows.
  Verify the installed desktop file's Exec after activation, not just the package.
- After package/source changes, test the actual current catalogue (`quest` search),
  official release resolution, isolated installation, and managed sync/list/update.
  An enum-only release fix does not establish catalogue compatibility. Prefer a
  supported upstream release to accumulating metadata compatibility patches.
  Search official publisher pages/TOCs too: catalogue absence does not establish
  source exclusivity (Wago projects may be missing from the catalogue).
- Keep the scheduled network updater restricted to its AddOns and tool data paths.
  `ProtectSystem` alone limits writes but still permits reading unrelated home data;
  retain home masking and verify both updater success and unrelated-path denial.

## Phoenix WoW Toolkit

- Standalone sources live in `AddOns/PhoenixWoWToolkit`. Read its README and AGENTS
  before changes; feature code, docs and tests belong inside their feature directory.
  Keep Nix installation and deployment fixtures here, outside the portable add-on.
- `wow.nix` owns `phoenix.wow.retailAddonDirectory` and Home Manager deployment.
  `deploy-toolkit.py` manages only the reserved store symlink, skips missing AddOns
  directories and preserves collisions. Never write to the real game as a test.
  Disable and activate the toolkit before removing the whole module or changing paths.
- The deployed package is immutable: checkout edits require deployment before a
  client reload/restart sees them. A restart cannot make undeployed code appear.

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

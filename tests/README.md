# Focused regression checks

Test implementations live with their owning modules; this directory is only an
index. Run from the repository root:

```sh
python3 -B -m unittest discover -s home/hue-lighting -p 'test_*.py'
node home/hue-lighting/test_panel.mjs
python3 home/mutable-json-settings/tests/mutable-json-settings.py
python3 modules/tests/mutable-settings-activation.py
python3 commands/tests/commands.py
python3 -B hosts/metal/storage-migration/test_restore.py
python3 -B hosts/metal/storage-migration/test_migrate.py
nix eval --impure --file modules/tests/target.nix
nix shell --inputs-from . nixpkgs#lua --command lua home/idle/tests/idle-blank.lua home/idle/blank.lua home/idle/black.frag
nix shell --inputs-from . nixpkgs#lua --command lua home/workspaces/tests/navigation.lua home/workspaces/navigation.lua
nix shell --inputs-from . nixpkgs#lua --command lua home/hyprland/gaming/windows/tests/game-windows.lua home/hyprland/gaming/windows/game-windows.lua home/hyprland/gaming/windows/classification.lua
nix shell --inputs-from . nixpkgs#lua --command lua home/hyprland/gaming/windows/tests/game-overrides.lua home/hyprland/gaming/windows/game-overrides.lua
nix shell --inputs-from . nixpkgs#lua --command lua home/kando/hyprland/tests/shortcuts.lua home/kando/hyprland/shortcuts.lua home/hyprland/gaming/windows/classification.lua
python3 -B modules/development/ai/agent/authorization/tests/request.py
python3 -B modules/development/ai/agent/tests/agent-admin.py
python3 -B modules/development/ai/agent/tests/agent-launch.py
python3 -B modules/development/ai/agent/tests/agent-history.py
python3 -B modules/development/ai/agent/tests/agent-review.py
nix eval --impure --file modules/development/ai/agent/tests/security-review.nix --apply 'f: f {}'
python3 -B modules/development/ai/agent/tests/agent-gui.py
python3 -B modules/development/ai/agent/tests/agent-gui-profile.py
python3 -B modules/development/ai/agent/tests/agent-gui-lifecycle.py
python3 -B modules/development/ai/agent/tests/agent-deployment.py
python3 -B modules/development/ai/agent/tests/source-manifest.py
python3 -B modules/development/ai/agent/tests/source-bootstrap.py
python3 -B modules/development/ai/agent/tests/policy-transition.py
python3 -B modules/services/updates/tests/update-runner.py
python3 -B modules/development/ai/agent/tests/upstream-review.py
python3 -B modules/development/ai/agent/tests/agent-gui-http.py
node modules/development/ai/agent/tests/agent-gui-http-hook.cjs
python3 -B modules/development/ai/agent/tests/agent-gui-connection.py
nix build --impure --file commands/tests/commands-packaging.nix --no-link
nix build --impure --file modules/security/tests/clamav-recovery.nix --no-link
nix build --impure --file home/hypr-persist/tests/hypr-persist.nix --no-link
nix build --impure --file home/kando/tests/packaging.nix --no-link
nix build --impure --file modules/input/keyd/tests/symbols.nix --no-link
python3 -B modules/input/mouse-side-button-debounce/test.py
python3 -B home/thunar/tests/thunar-archive.py
nix build --impure --file home/idle/tests/idle-command.nix --no-link
python3 -B home/timewall/tests/timewall.py
nix build --impure --file home/timewall/tests/timewall-packaging.nix --no-link
nix build --impure --file home/thunar/tests/thunar-packaging.nix --no-link
nix build --impure --file home/tests/caelestia-cli.nix --no-link
nix eval --impure --file modules/security/tests/opensnitch-observation.nix
nix eval --impure --file modules/security/tests/pam-desktop-conditional.nix
nix eval --impure --file modules/tests/desktop-services.nix
python3 -B modules/development/ai/agent/tests/reservation-deployment.py
```

- **Writer fixtures:** temporary homes cover initialization, writable regular
  files, legacy symlinks, read-only files, JSONC experiment preservation,
  object/array baseline types, idempotence, unrelated state, and failed writes.
- **Activation fixtures:** `nix-instantiate` renders the shared NixOS module with
  package and Home Manager stubs. Temporary targets exercise action selection,
  alternate config paths, conditional Caelestia inclusion, and failure propagation.
  This requires Nix but does not build packages or contact the daemon.
- **Command fixtures:** mocked execution covers host detection, environment
  precedence, argument handling, and session dispatch. The package fixture verifies
  the installed dispatcher ignores a rogue checkout script and build needs no sudo.
- **Storage migration fixtures:** disposable files/keys/databases exercise restore
  guards, metadata preservation, Syncthing/EFI checks, approval/failure sequencing,
  owned-resource cleanup and portable bundle contents. Provide Python 3, rsync,
  OpenSSL and ACL tools on PATH to avoid skipped coverage; target evaluation and
  command packaging also check the separate 4 TB target. No disk migration runs.
- **ClamAV fixture:** asserts configured unit relationships and tests recovery
  against a fake systemctl, including partially and fully active services.
- **Security evaluations:** assert OpenSnitch observation mode plus the inbound
  firewall, and desktop-dependent PAM services with the intended U2F routes.
- **Desktop evaluation:** asserts host-owned sessions, shared login/audio/power
  services, and absence of metal's retired KWin/reflow services.
- **Idle fixture:** a Lua interpreter mocks compositor options to check snapshot
  ownership, repeated callbacks, config reload and partial-write recovery. It
  never changes the live shader, cursor, locking or DPMS.
  The command fixture checks the exact upstream schema/IPC/idle-monitor API and
  executes patched manual-idle transitions, including duplicate activation,
  input resume, explicit restore and teardown.
- **Session fixture:** builds pinned hypr-persist with upstream tests, exact
  containment-launch override tests and guards for the audited no-close simple
  restore path. It checks private state/unit/logout declarations without starting
  a daemon or importing live session state. New files must be staged for its
  Git-flake source; logout/login and reboot restoration need manual acceptance.
- **Kando fixtures:** validate menus against the exact upstream 2.3 schemas and
  real context-selection method and managed launch paths. The parent fixture includes
  `home/kando/hyprland/tests/packaging.nix` for routing, rollback and the closed,
  non-root input unit. Fake events exercise stable-release debounce, unchanged
  high-resolution wheel events, recovery and cleanup without grabbing hardware.
  Portal shortcuts, focus, gestures and hotplug require manual acceptance.
- **Game-window fixtures:** `home/hyprland/gaming/windows/tests/` checks pure
  metadata classification, class overrides, initial rules and late tiling changes.
  It does not establish runtime fullscreen/workspace behavior.
- **Psysonic output fixture:** `modules/services/tests/psysonic-output.py` takes
  the pinned upstream source directory as its argument and needs patch, rustc,
  a C linker and Node 24. It checks device predicates and startup recovery using
  synthetic state; it never accesses the live app profile.
- **Wallpaper fixtures:** mock fixed commands and temporary files to check
  missing/invalid assets, FIFO rejection, theme boundaries, black fallback,
  quoting and serialized writes. Packaging checks actual executable/config paths
  and session-bound declarations; no user wallpaper is read or displayed.
- **Thunar fixture:** checks metal/VM declarations and applies the exact pinned
  Caelestia/Thunar patches. GTK under an isolated Xvfb verifies light/dark palette,
  icon/list/backdrop selection, file-monitor refresh, invalid last-good retention
  and shutdown cleanup. Generated ImageMagick samples verify literal filenames,
  batch collision safety, first-frame conversion and lossless JXL; originals stay
  intact. No live file-manager window, user image or desktop setting is touched.
  Quick ZIP fixtures cover collisions, literal filenames, overlapping selection,
  symlink preservation, special-file rejection and old timestamps.
- **Agent broker fixtures:** fixed commands, argument rejection, output/deadline
  bounds, named tracing reads, xHCI wakeup round-trip, malformed requests, and
  symlink escape rejection. These use temporary trees and mocked subprocesses;
  real systemd socket activation, root diagnostics, sysfs writes, and auditing
  require the [agent acceptance pass](../docs/AGENT_SANDBOX_ACCEPTANCE.md).
- **History fixtures:** disposable homes verify SQLite WAL backup, source and
  credential preservation, cold-writer refusal, lifecycle exclusion, interrupted
  staging recovery and conditional locations. Real listing/resume/archive and
  cross-client task writer exclusion require a coordinated cold handoff.
- **Agent launcher/review/GUI fixtures:** fail-closed stdio and login setup,
  frozen Git source, rejected/stale verdicts, process bounds, unsafe Git helper
  suppression, neutral direct-activation reasons, fixed `ai-broker` argument mapping
  and rejected missing reasons/commands/overrides, private profile/environment validation and real fixed-command socket relays.
  Desktop lifecycle fixtures reject upstream wiring drift before patching the
  Linux tray predicate; actual window close/reopen remains a runtime check.
  Protected deployment fixtures cover immutable source/closure binding, rejection
  before activation, bootstrap file safety and separate boot/runtime rollback.
  Security fixtures cover dirty snapshots, exact source/closure/policy cache reuse,
  diff-only input, two controller invocation bounds, requested frozen context,
  authenticated pending overrides and secret-safe failures. Oversized AI input
  and observed compaction fail explicitly; source transport has separate guards.
  The options fixture checks disabled defaults, fresh override authentication and
  opt-in shutdown declarations without enabling the live features.
  HTTP fixtures cover destination/header bounds, real identity/routing, streaming
  and cancellation without exposing credentials.
  Shared-GUI guard fixtures cover private lock modes, stale owner nonces and
  normal owner close before a fresh guard starts; the owner uses explicit Electron
  stubs. Set `PHOENIX_TEST_NODE` to an absolute Node executable when running
  `agent-gui-state.py` to include that combined workflow.
  `agent-gui-control.cjs` checks fixed actions, cancellation and connection bounds;
  `agent-gui-control-patch.py --source DIR` verifies the exact extracted pinned
  main bundle. GUI socket fixtures need sandbox execution permission; no OS root.
  Authorization presentation fixtures stub native UI and preflight/authentication,
  checking escaping, Cancel, unchanged frozen helper input, default-off direct
  clients, contained guidance and independent override flows. No dialog is opened.
  Command packaging checks preview exact immutable helpers, target and generated
  audit context plus rejected broker arguments; it performs no root preflight or
  host authentication. Deployment fixtures use explicit preflight/auth stubs.
  Separate sign-in, real model turns, desktop portal behavior and authenticated
  system activation remain runtime acceptance checks.

- **Update fixtures:** disposable Git repositories exercise candidate preparation,
  satisfied hold/patch cleanup after deterministic staging, failed-staging preservation,
  unrelated index/worktree edits and deferred user commits. Mocked public sources
  enforce exact publisher checks; automatic controller fixtures reject source/publisher changes and never invoke AI review. Manual upstream authority evidence rejects unknown or
  oversized sources. None runs the live updater or activates NixOS.

The `nix build` and `nix eval` commands above load the full flake and require Nix
daemon access; builds may download dependencies. None activates the system.

These checks were added for the architecture changes; they are not a
comprehensive runtime suite. They never alter live settings or activate NixOS.
Full-host evaluation/build and the combined manual acceptance pass still verify
actual Home Manager deployment, application reloads, and session/reboot behavior.

Protected desktop unit guarding (default off):
`python3 -B modules/development/ai/agent/tests/disruption.py` checks regenerated
immutable unit layouts, active-unit/removal/drop-in/dependency changes, native
no-restart behavior, inspection fallback, pending exception binding and both actual
helper routes using explicit fake OS/activation interfaces. See the module's
[proof limits](../modules/development/ai/agent/disruption.md); live acceptance is deferred.

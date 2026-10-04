# Focused regression checks

Run from the repository root:

```sh
python3 tests/mutable-json-settings.py
python3 tests/mutable-settings-activation.py
python3 tests/commands.py
nix shell --inputs-from . nixpkgs#lua --command lua tests/idle-blank.lua home/idle-blank.lua home/idle-black.frag
python3 -B tests/agent-admin.py
python3 -B tests/agent-launch.py
python3 -B tests/agent-review.py
python3 -B tests/agent-gui.py
python3 -B tests/agent-gui-profile.py
python3 -B tests/agent-gui-lifecycle.py
python3 -B tests/agent-deployment.py
python3 -B tests/agent-gui-http.py
node tests/agent-gui-http-hook.cjs
python3 -B tests/agent-gui-connection.py
nix build --impure --file tests/commands-packaging.nix --no-link
nix build --impure --file tests/clamav-recovery.nix --no-link
nix build --impure --file tests/hypr-persist.nix --no-link
nix build --impure --file tests/kando-packaging.nix --no-link
python3 -B tests/mouse-side-button-debounce.py
python3 -B tests/thunar-archive.py
nix build --impure --file tests/idle-command.nix --no-link
python3 -B tests/timewall.py
nix build --impure --file tests/timewall-packaging.nix --no-link
nix build --impure --file tests/thunar-packaging.nix --no-link
nix eval --impure --file tests/opensnitch-observation.nix
nix eval --impure --file tests/pam-desktop-conditional.nix
nix eval --impure --file tests/desktop-services.nix
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
  real context-selection method; check managed launch paths and the closed,
  non-root input unit. Fake events exercise stable-release debounce, unchanged
  high-resolution wheel events, recovery and cleanup without grabbing hardware.
  Portal shortcuts, focus, gestures and hotplug require manual acceptance.
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
- **Agent launcher/review/GUI fixtures:** fail-closed stdio and login setup,
  frozen Git source, rejected/stale verdicts, process bounds, unsafe Git helper
  suppression, private profile/environment validation and real fixed-command socket relays.
  Desktop lifecycle fixtures reject upstream wiring drift before patching the
  Linux tray predicate; actual window close/reopen remains a runtime check.
  Protected deployment fixtures cover immutable source/closure binding, rejection
  before activation, bootstrap file safety and separate boot/runtime rollback.
  They also reject oversized complete review inputs and any verdict after
  observed compaction, without omitting source to fit a bound.
  HTTP fixtures cover destination/header bounds, real identity/routing, streaming
  and cancellation without exposing credentials.
  GUI socket fixtures need sandbox execution permission; they need no OS root.
  Separate sign-in, real model turns, desktop portal behavior and authenticated
  system activation remain runtime acceptance checks.

The `nix build` and `nix eval` commands above load the full flake and require Nix
daemon access; builds may download dependencies. None activates the system.

These checks were added for the architecture changes; they are not a
comprehensive runtime suite. They never alter live settings or activate NixOS.
Full-host evaluation/build and the combined manual acceptance pass still verify
actual Home Manager deployment, application reloads, and session/reboot behavior.

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

# Desktop activation safety

## Intentions

Keep an existing graphical session usable when its configured packages change.
Build/evaluation success must not be presented as proof of live-session safety.

## Accepted graphics stack

`config/updates.json` holds `hyprland` at the package set used by the accepted
0.56.2 compositor and `linux_latest` at the accepted kernel 7.3 package set.
`config/desktop-packages.nix` applies these existing package-hold semantics to
metal's compositor/portal, overview plugin, IPC clients and kernel/NVIDIA module
set. Ordinary application updates continue using their declared inputs; the
shared unstable input is not globally downgraded. Holds have no automatic release
version: reproduce a cold login with a recoverable fallback on this NVIDIA
multi-monitor host before removing them. A successful build or headless fixture
does not establish physical display initialization.

The kernel hold is conservative recovery of the accepted pair, not a finding
that kernel 7.3.1 caused the login failures. Upstream reports a 0.57 NVIDIA modeset
regression ([discussion 16764](https://github.com/hyprwm/Hyprland/discussions/16764));
the retained local failure logs do not establish that exact mechanism.

## Live activation checks

`desktop.nix` registers `phoenixDesktop` in NixOS's native `system.preSwitchChecks`.
For `test`, `switch`, and the non-activating `check` action,
`desktop-live-check.py` compares each running Hyprland executable with the resolved
candidate executable. A different build or an inspection error stops activation.
The pinned Nixpkgs compiled wrapper is resolved to its `.Hyprland-wrapped`
executable; detection includes the kernel's truncated `.Hyprland-wrapp` name.
The comparison includes package/dependency changes, not just version numbers.
No running Hyprland, or the exact same executable, permits the operation.

This covers human `phoenix-test`/`phoenix-switch` through nixos-rebuild and the
broker's actual native activation. The broker also invokes the native `check`
action before profile changes and before entering its activation/rollback block:
a rejected preflight must not cause a disruptive rollback activation.
NixOS repeats its native checks when activation is actually attempted.

When blocked, use `phoenix-boot` and reboot when convenient. Boot staging does not
change the current desktop. Logging out/in alone starts the current installed
compositor; it does not apply a configuration that was only staged for next boot.
Do not disable pre-switch checks to work around the rejection.

The check prevents replacing the compositor configuration beneath an older
session. It does not validate all Lua options, predict every service restart,
detect every application crash, or promise safe graphics-driver replacement.
The workspace loader's version/deferred-load guards remain a second safeguard.
The separate experimental protected-unit guard remains disabled; see
[its scope and acceptance limits](development/ai/agent/disruption.md).

Run `python3 -B modules/tests/desktop-live-check.py`, the desktop-services Nix
fixture, and `modules/development/ai/agent/tests/agent-deployment.py` for the
identity, wiring and preflight/rollback contracts. These are not full desktop or
real activation acceptance; exercise any such trial with the operator idle.

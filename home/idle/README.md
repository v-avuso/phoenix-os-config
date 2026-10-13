# idle

Caelestia idle blanking helpers and pinned command-transition fixtures.

`../caelestia.nix` consumes these helpers; they are not a standalone module. Tests
and supporting fixtures live in `tests/`; run commands from the repository root using
the [test index](../../tests/README.md).

`blank` activates the black-screen idle action; `blank off` restores it. Both
use `caelestia shell idle ...`: the CLI itself adds the `ipc call` prefix.

Manual activation blanks after 100 ms of inactivity. A positive timeout is
required for the pinned Hyprland compositor to emit resume on mouse/keyboard
input; a zero timeout never resumes. Outputs retain their signal throughout.
If needed, run `blank off` to restore explicitly.

Caelestia uses its upstream user service on `hyprland-session.target`. Package
changes restart the shell, so IPC addresses the running version rather than a
stale store path. The compositor startup hook starts the target once; it does
not launch an additional unmanaged shell.

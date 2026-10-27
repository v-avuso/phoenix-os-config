# Hue edge lighting

## Intentions

- Synchronize only the center display's narrow left/right edges to the corresponding
  lamps, with one on/off control and one linked glow adjustment.
- Keep Huenicorn unpatched, credentials/profile state private and writable, and all
  control traffic on localhost. Start only on demand; no login/system service.

## Use

Launch **Hue Sync** from the application menu, or `phoenix-hue-control`.
The panel is at <http://127.0.0.1:8217>. Sync starts off. Check **Sync** to launch
Huenicorn; select only `HDMI-A-2` in the capture permission dialog when prompted,
and tick **Allow restore token** to remember that choice. Huenicorn saves the
portal's token privately and requests the same capture on later starts; the portal
can still ask again if permission expires or the display is unavailable.
**Choose screen…** stops the owned capture, clears only its saved restore token,
and restarts it to open the system picker. It requires sync to be enabled.
Pick another monitor there; edge sampling then follows that monitor.
Uncheck it to stop the owned process and release Entertainment streaming. This
stops synchronization; it does not promise to turn the lamps off or restore a scene.
Closing the browser tab leaves the panel/sync running. Reopen the launcher to
return to the same controls. The two navigation buttons open Huenicorn settings
and the bundled edge-color test; settings require sync to be enabled.
Terminating the panel process also stops its child.

**Glow boost** links gamma correction across every active channel in the selected
Entertainment profile and saves it through Huenicorn's API. `0` is neutral,
positive values brighten dim colors, negative values darken them, and black stays
black. This is not a linear brightness percentage. The three gradient channels of
each Signe lamp all follow the same edge; six channels do not mean six screen zones.
Neutral is at 25% of the slider: the dimming range occupies the first quarter,
and the brightening range occupies the remaining three quarters. Stored gamma
values and endpoints are unchanged; only slider spacing and precision change.
Avoid editing channel levels in Huenicorn's setup page simultaneously.

## Private setup

Huenicorn reads `~/.config/huenicorn/config.json` and its named profile. These
contain keys and bridge-specific state: never declare them as Nix files or commit
them. The controller requires an existing paired config, `boundBackendIP` set to
`127.0.0.1`, and `restServerPort` set to `8215`. Keep the directory mode `700`,
files `600`. Pairing and initial screen/area setup use upstream's local interface;
never launch its default all-interface server without a localhost config first.

The trial uses the separate **Linux edge trial** Entertainment area, with three
independent segments per lamp. Left channels use `(0,0)`–`(0.08,1)`; right channels
use `(0.92,0)`–`(1,1)`. Profile membership and IDs remain private runtime state.
At 3840×2160, native `subsampleWidth=3840` avoids downscaling across strip
boundaries; fractional pixel endpoints are rounded by upstream. `refreshRate=25`
sets the requested rate, not a measured delivery guarantee. Capture permission
may be requested again when toggling sync on; restoration requires the user's
permission in the picker and has not yet been confirmed in the host session.

The launcher limits OpenCV/OpenBLAS/OpenMP worker counts to one per library.
An initial 10-second native-resolution trial used 573% CPU; the combined limits
reduced a later sample to 42.6% (one CPU core = 100%), about 227 MiB RSS. These
samples are not a controlled game-performance comparison. User tests confirmed
independent whole-lamp response, interior exclusion, and fullscreen gameplay.
The operator also confirmed manual all-screen blank/return recovery without a
restart. Automatic idle blanking, video-only coverage and delivered FPS remain
unverified; do not infer them from a successful build or handshake.

## Ownership and decisions

- `package.nix` packages upstream Huenicorn 1.2.0 at an exact revision without
  patches, following its official flake recipe with Phoenix's locked package set.
  Upstream needs httplib 0.46 while Phoenix supplies 0.30, so only this dependency
  is pinned separately. Network dependency fetching during compilation is disabled.
- `control.py` owns one child process and a loopback HTTP API. Exact Host/Origin
  checks protect panel mutations; no shell commands or caller-selected executables
  are accepted over HTTP. Logs go to `~/.local/state/phoenix-hue-control/` with
  restrictive permissions. It never signals arbitrary/external Huenicorn instances.
- `panel.html` presents sync, screen selection and glow controls and saves completed slider
  changes. The native UI remains available for setup while sync is running; `edge-test.html`
  supplies the isolated red/blue test from the same panel server.
- `default.nix` supplies the manual launcher and desktop entry for the metal host.

Lumux's Entertainment path mixes top/bottom zones into lamp outputs. Lumen's
normal settings sample wider strips. Huenicorn's native rectangles passed the
strict isolation trial, but it lacks master brightness. A small API/process adapter
retains that proven capture path without a fork; linked gamma is an explicitly
accepted approximation. HyperHDR was inspected as a fallback with native luminance
adjustment; it has not been installed or runtime-validated here.

On Wayland, Huenicorn 1.2.0 delegates screen selection to the portal and exposes
no monitor-list/switch API. Its existing restore-token flow avoids repeated
selection after one approved choice; resetting the token follows the upstream
README's documented monitor-change procedure. A named-monitor dropdown and an
unconditionally preselected center monitor are not implemented. Hyprland's custom
picker setting is portal-wide, so changing it would also affect unrelated capture
clients. Keep that boundary rather than replace the proven capture path for this UI.

The upstream web UI has no authentication and bridge HTTPS verification is disabled
upstream. Loopback binding prevents LAN exposure, not control by other local
processes. The panel is not intended for remote access or reverse-proxy deployment.

## Checks

```sh
python3 -B -m unittest discover -s home/hue-lighting -p 'test_*.py'
node home/hue-lighting/test_panel.mjs
```

Tests exercise linked updates/save, input bounds, owned-child stopping, unsafe
binding rejection, capture reset/preservation, slider mapping and cross-origin/rebinding rejection using a disposable local
server. Build the metal Home Manager package/evaluate the host without activation.
A live check should toggle off/on, approve center capture with a restore token,
confirm a later start remembers it, use **Choose screen…** to switch and return,
move the single slider (neutral at 25%),
verify all active channels and the saved profile agree, then exercise edge isolation,
fullscreen content and ordinary blank/wake. Never force hibernation or restart
shared capture services to perform these checks.

Before activation, the user-level `phoenix-hue-control.desktop` entry and a private
Nix GC root provide the trial launcher. Remove that local desktop entry and trial
GC root after Home Manager has installed the declarative entry, so it owns future
launcher updates. This trial registration does not activate NixOS.

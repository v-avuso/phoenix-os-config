# Hue edge lighting

## Intentions

- Synchronize the selected source's narrow left/right edges to the corresponding
  lamps, with one on/off control and one linked glow adjustment.
- Require initial native source consent, remember that choice across starts, and
  keep the full source picker accessible for replacements.
- Keep Huenicorn unpatched, credentials/profile state private and writable, and
  control traffic on localhost. Start only on demand; no login/system service.

## Use

Launch **Hue Sync** from the application menu, or `phoenix-hue-control`.
The panel is at <http://127.0.0.1:8217>. Sync starts off. Enable **Sync**, then
select your preferred screen, window or region in the system picker. **Allow a
restore token** is checked by default for Hue; leave it checked to remember the
source. Later starts reuse the saved choice while the portal considers it valid.
Unchecking it intentionally asks again next time. Disconnected/changed displays
or revoked permissions may require a new selection.

**Lighting source settings…**, before Huenicorn settings at the bottom of the
card, stops the owned capture, forgets only its saved source token, and opens the
full Screen/Window/Region picker again. The replacement is remembered by the same
native flow. Edge color test has its own row. No monitor connector is hardcoded.
A direct dropdown is omitted because Huenicorn exposes no monitor-list/switch API
and the accepted remembered-source workflow retains system consent.

Disable **Sync** to stop the owned process and release Entertainment streaming.
This does not promise to turn lamps off or restore a scene. Closing the browser
tab leaves the panel/sync running; reopening the launcher returns to it.
Terminating the panel process stops its child.

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
uses the native portal approval and restore-token flow. Builds and isolated portal
checks do not establish saved-source restoration on the shared desktop.
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
- `sources.py` supplies the native remember-checkbox default; `portal-picker.py`
  always executes the original native picker, preserving other applications' args.
- `default.nix` supplies the on-demand launcher, desktop entry and custom-picker
  wiring. `portal.nix` and `portal-app-id.patch` forward app identity to that hook
  in the pinned Hyprland portal; the metal host selects this package.

Lumux's Entertainment path mixes top/bottom zones into lamp outputs. Lumen's
normal settings sample wider strips. Huenicorn's native rectangles passed the
strict isolation trial, but it lacks master brightness. A small API/process adapter
retains that proven capture path without a fork; linked gamma is an explicitly
accepted approximation. HyperHDR was inspected as a fallback with native luminance
adjustment; it has not been installed or runtime-validated here.

On Wayland, Huenicorn 1.2.0 delegates source selection to the portal and exposes
no monitor-list/switch API. A custom picker alone cannot identify its caller in
Hyprland portal 1.4.1. The small pinned patch passes the existing request app ID
through as `XDPH_APP_ID`. Huenicorn runs in a fresh on-demand
`app-org.phoenix.HueSync-RANDOM.scope`, following the [desktop application unit
convention](https://systemd.io/DESKTOP_ENVIRONMENTS/); the [portal frontend's native
host-app detection](https://github.com/flatpak/xdg-desktop-portal/blob/1.20.4/src/xdp-app-info-host.c)
extracts that identity. `systemd-run --scope` executes the workload in the owned
child process, preserving the controller's stop semantics. No login service or
capture-engine fork is added.

Application IDs are forgeable UX hints, not authentication. Matching Hue only
checks the native picker's **Allow a restore token** checkbox; it never returns a
selection or grants capture. Every initial request still needs the user to select
and approve a source. Other applications retain the original picker arguments.
The native portal validates token restoration and Huenicorn saves replacement
tokens in its private config. Normal starts never remove them. Revisit the small
patch on portal upgrades; its version assertion is deliberate.

The upstream web UI has no authentication and bridge HTTPS verification is disabled
upstream. Loopback binding prevents LAN exposure, not control by other local
processes. The panel is not intended for remote access or reverse-proxy deployment.

## Checks

```sh
python3 -B -m unittest discover -s home/hue-lighting -p 'test_*.py'
node home/hue-lighting/test_panel.mjs
```

Tests exercise linked updates/save, input bounds, owned-child stopping, unsafe
binding rejection, token preservation and explicit reset, native picker routing,
slider mapping and cross-origin/rebinding rejection with a disposable local server.

`tests/portal-runtime.py` uses a private session bus and disposable configuration.
Its native-picker stand-in records arguments and declines selection. Both Hue and
an unrelated app must fail capture; only Hue receives the remember-checkbox flag.
It never changes live desktop services, Huenicorn state or lamps:

```sh
python3 -B home/hue-lighting/tests/portal-runtime.py \
  --portal "$portal_package" --frontend "$portal_frontend" \
  --picker-config "$picker_config" --probe-python "$gio_python"
```

After deployment, select your preferred source once, toggle sync off/on, and
confirm no picker appears. Change **Lighting source settings…**, select a
replacement and repeat. Confirm the checkbox can still be unchecked and other
applications retain their native picker. These are operator desktop acceptance
checks, separate from build/isolated fixture results.

Home Manager owns the launcher/desktop entry. Apply the new portal package and
configuration through its normal desktop service lifecycle. Existing captures
belong to the portal instance that created them; refreshing the panel alone does
not replace it. Never restart shared capture services merely for validation.

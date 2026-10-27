# Hue edge lighting

## Intentions

- Synchronize the configured default display's narrow left/right edges to the
  corresponding lamps, with one on/off control and one linked glow adjustment.
  Start on the second display from the left without a source-selection dialog;
  keep live display changes and the full system source picker accessible.
- Keep Huenicorn unpatched, credentials/profile state private and writable, and all
  control traffic on localhost. Start only on demand; no login/system service.

## Use

Launch **Hue Sync** from the application menu, or `phoenix-hue-control`.
The panel is at <http://127.0.0.1:8217>. Sync starts off. Check **Sync** to launch
Huenicorn. The default is declared by `phoenix.hue.defaultScreen = 2` in the host's
Home Manager configuration. Displays are numbered **from one, left to right** by
current desktop position, not by connector name, compositor ID, or the system
picker's zero-based labels. The second display is selected automatically. Moving
from HDMI to DisplayPort keeps the default position; rearranging the desktop can
change which physical display occupies it. If the configured position is missing,
sync refuses to start until you choose a connected display.

The **Source display** dropdown lists live display descriptions and switches
capture directly, restarting only the owned Huenicorn process when sync is on.
You can also choose a display before enabling sync. This override lasts for the
panel process; reopening the browser tab reuses it. Relaunching the panel reasserts
the declarative default.

**Lighting source settings…** opens Hyprland's full sharing picker, including
Screen, Window and Region. Its selection remains in use until you select a display
in the dropdown or relaunch the panel. In that manual mode, **Allow restore token**
can remember the chosen source across sync toggles. Automatic display mode resolves
the current connector on every start and does not rely on connector-bound tokens.
Uncheck it to stop the owned process and release Entertainment streaming. This
stops synchronization; it does not promise to turn the lamps off or restore a scene.
Closing the browser tab leaves the panel/sync running. Reopen the launcher to
return to the same controls. The bottom controls provide lighting-source selection, Huenicorn settings, and
the bundled edge-color test on a separate row; settings require sync to be enabled.
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
uses the app-specific automatic selector in display mode, or the normal portal
permission/restore-token flow in manual mode. An isolated private-bus trial selected
the configured output without a click and returned a 3840×2160 capture source.
Shared-desktop workflow and lamp-response acceptance remain separate live checks.

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
- `sources.py` owns live display ordering, default resolution and the runtime
  preference format; `portal-picker.py` adapts that preference to the native picker
  protocol and otherwise executes the original Screen/Window/Region UI.
- `default.nix` supplies the on-demand launcher, default-screen option, desktop
  entry, and `hypr/xdph.conf` custom-picker wiring. `portal.nix` and
  `portal-app-id.patch` expose request application identity to that existing hook
  in the exact pinned Hyprland portal; the metal host selects this package.

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

Only that nonempty Hue app ID and a connected output in its explicit runtime
preference can return an automatic selection. Other IDs, absent/broken preferences,
missing outputs, and manual mode retain the original picker. Preferences live in
`$XDG_RUNTIME_DIR/phoenix-hue-control/source.json`; bridge credentials/profile state
stay separate. Automatic mode removes Huenicorn's old restore token after stopping
its owner, so a saved window/connector cannot take precedence over the default.
Application IDs are UX routing, not an authentication boundary: unsandboxed
same-user applications can impersonate them. The adapter grants no root/LAN access.
The hook is global, so its unchanged fallback for unrelated apps is an essential
contract. Revisit the patch on portal upgrades; its version assertion is deliberate.

The upstream web UI has no authentication and bridge HTTPS verification is disabled
upstream. Loopback binding prevents LAN exposure, not control by other local
processes. The panel is not intended for remote access or reverse-proxy deployment.

## Checks

```sh
python3 -B -m unittest discover -s home/hue-lighting -p 'test_*.py'
node home/hue-lighting/test_panel.mjs
```

Tests exercise linked updates/save, input bounds, owned-child stopping, unsafe
binding rejection, capture reset/preservation, spatial defaults, Hue-only picker
routing, slider mapping and cross-origin/rebinding rejection using a disposable
local server. Build the metal Home Manager package/evaluate the host without activation.

`tests/portal-runtime.py` exercises real source selection on a separate session bus
with private configuration, data and runtime preferences. It launches the built
portal/frontend, scopes a probe as Hue, checks the selected output and closes the
capture. Its native-picker fallback deliberately fails instead of opening a dialog,
so success requires the automatic route. It does not change the live portal,
Huenicorn config or lamps. Pass the built patched portal package, the native
frontend executable, built `xdg.configFile."hypr/xdph.conf".source`, and a Python
executable providing `gi.repository.Gio`:

```sh
python3 -B home/hue-lighting/tests/portal-runtime.py \
  --portal "$portal_package" --frontend "$portal_frontend" \
  --picker-config "$picker_config" --probe-python "$gio_python"
```

A live check should enable sync without a picker, confirm the configured display,
switch displays through the dropdown, toggle off/on, and use **Lighting source
settings…** to select a window/region and return to display mode. Confirm unrelated
applications still open the original picker. Then move the single slider (neutral at 25%),
verify all active channels and the saved profile agree, then exercise edge isolation,
fullscreen content and ordinary blank/wake. Never force hibernation or restart
shared capture services to perform these checks.

Home Manager owns the launcher/desktop entry. After an authorized deployment,
relaunch the panel and apply the portal package/configuration through the normal
desktop service lifecycle. Existing captures still belong to the portal instance
that created them; do not assume refreshing the web page replaces that instance.

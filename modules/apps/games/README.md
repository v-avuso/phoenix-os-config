# Gaming

This module enables Steam, installs Lutris, and packages game-specific compatibility support.
It is imported by [`modules/apps`](../README.md).

Lutris uses `pkgs.lutris-free`; its library and runner settings remain user-managed.
Steam already enables 32-bit graphics support through its NixOS module, so this
module does not duplicate that option or add standalone Wine packages.

## Steam UI scaling

Hyprland uses the shared `1.6` desktop scale in
[`config/desktop-scale.nix`](../../../config/desktop-scale.nix). Steam owns its
UI scale in mutable client settings; Phoenix does not write or replace Steam's
configuration. To match the desktop scale, set Steam's native
**Settings → Accessibility → UI Scaling** slider to **160%**. Steam does not
expose a supported declarative setting for this slider. Avoid the obsolete
`STEAM_FORCE_DESKTOPUI_SCALING` override.

## No Man's Sky DLSS Frame Generation

The module builds the single-file Vulkan-layer workaround from
[Proton issue #438, comment 5902067647](https://github.com/ValveSoftware/Proton/issues/438#issuecomment-5902067647).
The report traces the DLSS-G hang to NVIDIA Streamline submitting two waits on
the same binary semaphore across queues. The layer shadows affected semaphores
with a private timeline semaphore when `NMS_FIX_SHADOW=1`. The related
[Streamline issue #127](https://github.com/NVIDIA-RTX/Streamline/issues/127)
tracks the upstream bug. Phoenix packages the upstream C source and manifest,
substituting a Nix-store library path at build time. It does not modify Proton.

To scope the workaround to No Man's Sky only, set this in that game's Steam
Properties → General → Launch Options (App ID **275850**):

```text
VK_ADD_LAYER_PATH=/run/current-system/sw/share/vulkan/explicit_layer.d VK_INSTANCE_LAYERS=VK_LAYER_NMS_fix NMS_FIX_SHADOW=1 DXVK_NVAPI_VKREFLEX=1 WINE_DISABLE_HARDWARE_SCHEDULING=0 %command%
```

Enable regular **2× DLSS Frame Generation** in the game. Steam stores these
launch options per game; do not set the variables in the global session
environment. The layer is installed system-wide but remains unloaded unless
requested. `VK_ADD_LAYER_PATH` adds the manifest directory without replacing
the Vulkan loader's standard search paths.

Remove the package and launch options only after a shipped No Man's Sky update
or Proton/Streamline update fixes the semaphore issue and the fix is verified
by loading a save and playing through the former loading-screen hang with
regular DLSS Frame Generation enabled and without this layer. Track that
condition against [Proton #438](https://github.com/ValveSoftware/Proton/issues/438)
and [Streamline #127](https://github.com/NVIDIA-RTX/Streamline/issues/127).

## World of Warcraft Retail (metal-4tb)

### Intentions

Manage release archives in the existing Lutris/Battle.net Retail AddOns directory,
without moving the installation, writing WTF, adopting unrelated add-ons, or
controlling the game. `wow.nix` owns the package, dedicated `phoenix-retail`
profile and user `v`'s daily 09:00 Europe/Berlin timer. `Persistent=true` catches
missed runs when the user manager returns; it does not wake the computer.

Edit [`wow-addons.json`](wow-addons.json) to declare desired source URIs. The
small `wow-addons sync` adapter queries instawow's native JSON list and installs
missing entries. Each timer run syncs then executes `instawow update`. Removing
an entry never deletes an add-on: removal remains an explicit operator action.
Instawow's SQLite database, cache, profile and rollback history remain mutable;
the manifest is an additive desired set, not a mirror of all installed add-ons.

```sh
wow-addons sync                         # apply manifest additions
wow-addons install github:owner/repo    # immediate addition; also edit manifest
wow-addons list --format detailed
wow-addons update
wow-addons remove github:owner/repo     # remove from manifest first
wow-addons rollback github:owner/repo
systemctl --user start wow-addons-update.service
systemctl --user list-timers wow-addons-update.timer
journalctl --user -u wow-addons-update.service
```

CLI and timer operations share a one-hour-wait flock; the oneshot cannot overlap
itself. Use `wow-addons` for this profile to retain that lock. Errors propagate
from instawow to systemd; stdout/stderr go to the journal under the host's journal
retention policy. The service limits writes to AddOns and tool state/cache and
makes WTF read-only. There is no game-process check, signal, restart or reload.
Existing unmanaged folders cause an installation conflict rather than replacement;
back them up and explicitly select `wow-addons install --replace SOURCE` only
when adoption is intended. Never use automatic whole-directory reconciliation.

Sources: [ElvUI via Tukui](https://github.com/tukui-org/ElvUI),
[ToxiUI releases](https://github.com/Toxicom/toxiui/releases), and
[WindTools releases](https://github.com/wind-addons/ElvUI_WindTools/releases).
The locked Nixpkgs instawow 7.0.0.post1 needs the enum-only Forever metadata
backport from [upstream v7.2.0](https://github.com/layday/instawow/blob/v7.2.0/src/instawow/_sources/github.py)
to read WindTools' mixed-flavour release metadata. Remove the backport once the
locked package contains it, after testing these sources. No flake input changes.
[Instawow](https://github.com/layday/instawow) supports native profiles, rollback
and GitHub ZIP release assets. CurseForge resolution was tested and reports
`access token missing`; author distribution restrictions can further prevent
downloads. These three sources require no CurseForge key. Do not commit tokens.

Updates may write files while WoW is running. Already loaded Lua remains in memory;
this is not hot patching. Manually reloading during an update can read a mixed
version; wait for the service to finish. A later manual `/reload` may reload
existing add-ons, while newly installed add-ons or changed file discovery may
require exiting and reopening WoW. No in-game reload/restart is automated.
Actual in-game behaviour and UI compatibility require player acceptance; successful
archive installation/update and unchanged WTF hashes do not prove those outcomes.

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

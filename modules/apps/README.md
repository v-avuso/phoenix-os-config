# Desktop apps

## Gaming

`games.nix` enables the system Steam program and permits its unfree package.

### No Man's Sky DLSS Frame Generation

`games.nix` builds and installs the single-file Vulkan-layer workaround from
[Proton issue #438, comment 5902067647](https://github.com/ValveSoftware/Proton/issues/438#issuecomment-5902067647).
The report traces the DLSS-G hang to NVIDIA Streamline submitting two waits on
the same binary semaphore across queues. The layer shadows affected semaphores
with a private timeline semaphore when `NMS_FIX_SHADOW=1`. The associated
[Streamline issue #127](https://github.com/NVIDIA-RTX/Streamline/issues/127)
tracks the upstream bug. Phoenix packages the upstream C source and its layer
manifest, replacing the manifest's developer-local library path with the Nix
store path at build time. It does not modify Proton.

To scope the workaround to No Man's Sky only, set this in that game's Steam
Properties → General → Launch Options (App ID **275850**):

```text
VK_ADD_LAYER_PATH=/run/current-system/sw/share/vulkan/explicit_layer.d VK_INSTANCE_LAYERS=VK_LAYER_NMS_fix NMS_FIX_SHADOW=1 DXVK_NVAPI_VKREFLEX=1 WINE_DISABLE_HARDWARE_SCHEDULING=0 %command%
```

Enable regular **2× DLSS Frame Generation** in the game. The launch options are
stored by Steam for that game; do not put these variables in the global session
environment. The layer is installed system-wide but remains unloaded unless a
process explicitly requests it. `VK_ADD_LAYER_PATH` adds the package's manifest
directory without replacing the Vulkan loader's normal search paths.

Remove the package and per-game launch options only after a shipped No Man's Sky
update or Proton/Streamline update fixes the semaphore issue and the fix is
verified by loading a save and playing through the former loading-screen hang
with regular DLSS Frame Generation enabled, without this layer. Track that
condition against [Proton #438](https://github.com/ValveSoftware/Proton/issues/438)
and [Streamline #127](https://github.com/NVIDIA-RTX/Streamline/issues/127).

Hyprland uses the shared `1.6` desktop scale in
[`config/desktop-scale.nix`](../../config/desktop-scale.nix). Steam currently
owns its UI scale in mutable client settings, so Phoenix does not write or
replace Steam's configuration. To match the desktop scale, set Steam's native
**Settings → Accessibility → UI Scaling** slider to **160%**. Steam does not
expose a supported declarative setting for this slider; avoid the obsolete
`STEAM_FORCE_DESKTOPUI_SCALING` override.

## Typst document publishing

The [documents module](documents/typst/README.md) installs Typst and makes
Phoenix's Omd2Typst-compatible template adapters available under
`~/.local/share/phoenix/typst/templates`. Omd2Typst itself remains managed per
Obsidian vault.

## Desktop media viewers

`media-viewers.nix` owns the Home Manager viewer settings and video, audio,
and image MIME defaults. Thunar uses the packaged `mpv.desktop` and
`swayimg.desktop` entries. Browser, directory, and other defaults retain their
existing owners.

mpv opens local video and audio in its built-in pseudo-GUI, with controls that
appear on mouse movement and hide automatically. Embedded album artwork takes
priority when available. The entire playlist repeats indefinitely, including a
single file; neighboring files are not automatically added. Psysonic remains the Navidrome library client; its
pinned version cannot open arbitrary local audio paths. Gwenview remains
available through Open With for image editing/conversion.

swayimg starts without an information overlay (`i` toggles it). Opening one image
also loads adjacent images in the same directory, sorted alphabetically.

| Input | Viewer action |
| --- | --- |
| Left / Right | Previous / next image |
| Wheel up / down | Zoom in / out around the pointer |
| Ctrl + wheel | Pan vertically |
| Alt + wheel | Pan horizontally |
| Shift + wheel | Previous / next image |
| Down | Pan vertically |
| Up / F11 / F | Toggle fullscreen |
| Left mouse drag | Pan |
| Backspace | Restore optimal zoom and centered position |

After authorized activation, double-click a JPEG or JXL in Thunar and check
adjacent-image navigation, pointer-centered zoom, modified-wheel panning,
fullscreen, drag, and Backspace reset. Check MP4/WebM playback and OPUS/MP3
playback with and without embedded artwork in mpv.

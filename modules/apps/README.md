# Desktop apps

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

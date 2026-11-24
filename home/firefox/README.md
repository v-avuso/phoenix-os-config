# Firefox

## Intentions

Keep the hardened and compatibility profiles reproducible and retain the clean
profile as an extension-free fallback. Aloud adds local reading and MP3 export
through the existing profile extension packages.

## Aloud

In Aloud **Settings → Voice**, download **Phonon** once per profile. A fresh
install uses **Zoey** (American English). If you already chose another voice,
use the English voice board to assign a Phonon voice. The Phonon model is
licensed for non-commercial use and runs on the CPU.

Download **Kokoro** separately to keep it available as an alternative. In
**Settings → Advanced**, keep **Use WebGPU acceleration when available** enabled
and check whether Aloud detects a GPU. The Nix configuration enables Firefox
WebGPU for pages and workers in both Aloud profiles. Aloud automatically
selects full-precision Kokoro on a supported GPU and quantized Kokoro on CPU.
Voice selections and downloaded models are managed by Aloud in each profile.

To check the workflow after setup, preview Zoey from the voice list. On a
regular web page, select a paragraph and choose **Read selection aloud** from
the context menu. Switch tabs and check that playback continues. With the page
still open and the network disconnected, use **Save as MP3 → Make the MP3 →
Save file** in the reading bar and play the saved file.

Keep Firefox's **Work Offline** mode off for this check. It can block Aloud's
packaged model manifest even when the voice model is already on disk.
